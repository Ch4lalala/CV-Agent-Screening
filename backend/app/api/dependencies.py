from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.services.development_user import get_development_user

DatabaseSession = Annotated[Session, Depends(get_db)]
DevelopmentUser = Annotated[User, Depends(get_development_user)]

