from pydantic import BaseModel


class Model(BaseModel): ...


class ResultModel(Model):
    keyword: str
