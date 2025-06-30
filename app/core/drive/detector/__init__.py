import platform

system = platform.system().lower()

if system == "linux":
    import linux
elif system == "darwin":
    import mac
elif system == "windows":
    import windows
else:
    raise NotImplementedError(f"SystemInfo not supported on platform: {system}")
