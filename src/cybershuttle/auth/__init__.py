from .device_auth import DeviceFlowAuthenticator

context = DeviceFlowAuthenticator(
    client_id="cybershuttle-agent",
    realm="10000000",
    auth_server_url="https://auth.cybershuttle.org",
)


def login():
    context.login()


def logout():
    context.logout()
