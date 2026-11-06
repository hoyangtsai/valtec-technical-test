"""HTTP API for the Valtec ArduPilot simulation MVP."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from .drone import DroneController, DroneError

controller = DroneController()


@asynccontextmanager
async def lifespan(_: FastAPI):
    controller.connect()
    try:
        yield
    finally:
        controller.close()


app = FastAPI(
    title="Valtec Drone Control API",
    description="MVP controls for one simulated ArduPilot quadcopter.",
    version="0.1.0",
    lifespan=lifespan,
)


class TakeoffRequest(BaseModel):
    altitude_m: float = Field(
        default=5,
        ge=1,
        le=20,
        description="Target height in metres above the takeoff point",
    )


class GotoRequest(BaseModel):
    latitude: float = Field(
        ge=-90,
        le=90,
        description="Target latitude in decimal degrees",
    )
    longitude: float = Field(
        ge=-180,
        le=180,
        description="Target longitude in decimal degrees",
    )
    altitude_m: float = Field(
        ge=1,
        le=20,
        description="Target height in metres above the takeoff point",
    )


def run(action):
    try:
        return action()
    except DroneError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse(url="/docs")


@app.get("/status", summary="Read the current simulated drone state")
def status():
    return run(controller.status)


@app.post("/takeoff", summary="Arm and take off in Guided mode")
def takeoff(request: TakeoffRequest):
    return run(lambda: controller.takeoff(request.altitude_m))


@app.post("/land", summary="Land at the current position")
def land():
    return run(controller.land)


@app.post("/goto", summary="Fly to a global position in Guided mode")
def goto(request: GotoRequest):
    return run(
        lambda: controller.goto(
            request.latitude,
            request.longitude,
            request.altitude_m,
        )
    )


@app.post("/rtl", summary="Return to the launch point and land")
def rtl():
    return run(controller.rtl)
