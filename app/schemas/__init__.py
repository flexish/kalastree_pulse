"""
Pydantic schemas.

Request and response contracts for the API layer. Every router should
validate incoming data against a schema here rather than reading raw
dicts, and return schema instances rather than ad-hoc JSON.
"""
