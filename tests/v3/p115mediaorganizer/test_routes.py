"""Verify FastAPI can register production endpoint signatures without a live host."""

from __future__ import annotations

import ast
import importlib.util
import unittest
from pathlib import Path
from typing import Optional

from .test_workflow import PLUGIN_DIR, Response, ns, plan, plugin


@unittest.skipUnless(
    importlib.util.find_spec("fastapi"), "Install FastAPI for route contract tests"
)
class RouteContractTest(unittest.TestCase):
    def setUp(self):
        from fastapi import FastAPI, Request, HTTPException
        from fastapi.testclient import TestClient
        from pydantic import BaseModel

        class Envelope(BaseModel):
            success: bool = True
            message: str = ""
            data: object = None

        # Compile endpoint methods with actual FastAPI annotation objects.
        self.globals = dict(ns)
        self.globals.update(Request=Request, HTTPException=HTTPException)
        tree = ast.parse((PLUGIN_DIR / "usability.py").read_text())
        tree.body = [
            n
            for n in tree.body
            if not isinstance(n, ast.ImportFrom)
            or n.module in ("__future__", "collections", "importlib.metadata")
        ]
        exec(compile(tree, "usability.py", "exec"), self.globals)
        self.p = plugin()
        self.p.save_data("last_plan", plan(self.p))
        self.p._p115_ops = lambda: type("Ops", (), {"available": True})()
        self.p._submit_task = lambda kind: Response(data={"kind": kind})
        self.p._require_admin_session = lambda request: None
        app = FastAPI()
        methods = {
            "workflow_status_api": ("GET", "/workflow"),
            "validate_config_api": ("POST", "/validate_config"),
            "prepare_execute_api": ("POST", "/execute/prepare"),
            "confirm_execute_api": ("POST", "/execute/confirm"),
            "records_api": ("GET", "/records"),
        }
        for name, (method, path) in methods.items():
            func = getattr(self.globals["UsabilityMixin"], name).__get__(self.p)

            def wrapper_factory(func):
                import inspect
                import typing

                def wrapper(*args, **kwargs):
                    result = func(*args, **kwargs)
                    return {
                        "success": result.success,
                        "message": result.message,
                        "data": result.data,
                    }

                hints = typing.get_type_hints(func)
                signature = inspect.signature(func)
                wrapper.__signature__ = signature.replace(
                    parameters=[
                        parameter.replace(
                            annotation=hints.get(name, parameter.annotation)
                        )
                        for name, parameter in signature.parameters.items()
                    ]
                )
                return wrapper

            app.add_api_route(
                path, wrapper_factory(func), methods=[method], response_model=Envelope
            )
        self.app = app
        self.client = TestClient(app)

    def test_request_injection_and_json_body_confirmation(self):
        response = self.client.post("/execute/prepare")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        token = response.json()["data"]["token"]
        response = self.client.post("/execute/confirm", json={"token": token})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_query_pagination_and_validation_payload(self):
        response = self.client.get("/records?page=1&page_size=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["items"]), 1)
        response = self.client.post(
            "/validate_config", json={"config": {"source_mappings": "bad"}}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertTrue(response.json()["data"]["errors"])
        self.app.openapi()
