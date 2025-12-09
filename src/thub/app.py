"""
FastAPI application for Tufts Hub.
"""

from fastapi import FastAPI


app = FastAPI(title="Tufts Hub")


@app.get("/")
async def root():
    """
    Root endpoint placeholder.
    """
    return {"message": "Tufts Hub is running"}
