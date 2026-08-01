"""
Service layer.

Business logic and integrations (Google Sheets, tree-growth rules, AI
insights, ...) live here, behind plain functions/classes that routers call.
Routers stay thin — they parse the request, call a service, and render or
return the result. This is what keeps later phases (Sheets, AI, KPIs)
additive instead of requiring a rewrite of the request-handling code.
"""
