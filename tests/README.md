# FastAPI pytest suite

Install:

    pip install -r requirements-test.txt

Run all tests:

    pytest -v

Run authentication tests:

    pytest tests/test_auth.py -v

Run one test:

    pytest tests/test_auth.py::test_refresh_success -v

The suite mocks MongoDB and security helpers, so normal tests do not modify
your development database.

Expected project module paths:

- app.main
- app.routes.auth
- app.routes.users
- app.routes.system
- app.utils.dependencies
- app.utils.security

If your files use different module paths, update the patch strings in tests.
