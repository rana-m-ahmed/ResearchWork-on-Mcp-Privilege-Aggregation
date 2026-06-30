from phase3.core.mcp_environment import MCPEnvironment
env = MCPEnvironment(mode="host-local")
res = env.execute("get_local_weather", {})
print("RESULT:", res)
