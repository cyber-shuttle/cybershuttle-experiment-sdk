from __future__ import annotations

authContext = None


def login():
    global authContext
    authContext = "1234"


def logout():
    global authContext
    authContext = None
