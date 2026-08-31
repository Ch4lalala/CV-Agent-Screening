from pydantic import BaseModel, ConfigDict


class OrmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

