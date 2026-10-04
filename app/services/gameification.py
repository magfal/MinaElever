from pydantic import BaseModel, Field
from app.models import PointRuleType, PointLimitPeriod

class BaseValueParameters(BaseModel):
    xp: int = Field(ge=0)

class LimitParameters(BaseModel):
    max_awards: int = Field(gt=0)
    period: PointLimitPeriod

class MultiplierParameters(BaseModel):
    factor: float = Field(ge=0)

class PercentBonusParameters(BaseModel):
    percent: float = Field(ge=0)
    condition: str
    minimum_days: int = Field(gt=0)

RULE_PARAMETER_MODELS = {
    PointRuleType.BASE_VALUE: BaseValueParameters,
    PointRuleType.LIMIT: LimitParameters,
    PointRuleType.MULTIPLIER: MultiplierParameters,
    PointRuleType.PERCENT_BONUS: PercentBonusParameters,
}

def validate_point_rule_parameters(rule_type: PointRuleType, parameters: dict) -> dict:
    model = RULE_PARAMETER_MODELS[rule_type]
    validated = model.model_validate(parameters)
    return validated.model_dump()