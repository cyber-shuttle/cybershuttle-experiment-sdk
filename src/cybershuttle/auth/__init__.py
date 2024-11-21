from .device_auth import DeviceFlowAuthenticator

context = DeviceFlowAuthenticator()


def login():
    context.login()


def logout():
    context.logout()
