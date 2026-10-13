from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _RuleBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool = True
    hold_seconds: int = Field(default=0, ge=0)
    cooldown_seconds: int = Field(default=0, ge=0)


class RapidChangeRuleIn(_RuleBase):
    field: Literal["ph", "tss", "debit"]
    rule_type: Literal["rapid_change"]
    secondary_field: None = None
    window_seconds: int = Field(ge=1)
    min_points: int = Field(ge=2)
    abs_delta: float | None = Field(default=None, ge=0)
    percent_delta: float | None = Field(default=None, ge=0)
    minimum_baseline: float | None = Field(default=None, ge=0)
    trigger_mode: Literal["any", "all"] = "any"

    @model_validator(mode="after")
    def has_a_configured_detector(self):
        if self.abs_delta is None and self.percent_delta is None:
            raise ValueError("rapid_change requires abs_delta or percent_delta")
        return self


class FlowStateRuleIn(_RuleBase):
    field: Literal["debit"]
    rule_type: Literal["flow_state"]
    secondary_field: None = None
    no_flow_threshold: float = Field(ge=0)
    low_flow_threshold: float = Field(ge=0)
    recovery_threshold: float = Field(ge=0)

    @model_validator(mode="after")
    def ordered_thresholds(self):
        if not self.no_flow_threshold <= self.low_flow_threshold < self.recovery_threshold:
            raise ValueError(
                "no_flow_threshold must be <= low_flow_threshold < recovery_threshold"
            )
        return self


class LowFlowTssRuleIn(_RuleBase):
    field: Literal["debit"]
    rule_type: Literal["low_flow_tss"]
    secondary_field: Literal["tss"]


OperationalRuleIn = Annotated[
    RapidChangeRuleIn | FlowStateRuleIn | LowFlowTssRuleIn,
    Field(discriminator="rule_type"),
]


class MonitoringConfigUpdate(BaseModel):
    cadence_seconds: int = Field(ge=1, le=86400)
    stale_after_seconds: int = Field(ge=1, le=86400)
    max_chart_points: int = Field(ge=60, le=1440)
    max_range_days: int = Field(ge=1, le=366)
    rules: list[OperationalRuleIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def stale_timeout_covers_one_cadence(self):
        if self.stale_after_seconds < self.cadence_seconds:
            raise ValueError("stale_after_seconds must be at least cadence_seconds")
        identities = [(rule.field, rule.rule_type) for rule in self.rules]
        if len(identities) != len(set(identities)):
            raise ValueError("rules must not repeat a field and rule_type combination")
        return self


class _OperationalRuleOutBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    is_active: bool
    hold_seconds: int | None
    cooldown_seconds: int | None
    updated_by_user_id: int | None


class RapidChangeRuleOut(_OperationalRuleOutBase):
    field: Literal["ph", "tss", "debit"]
    secondary_field: None
    rule_type: Literal["rapid_change"]
    window_seconds: int
    min_points: int
    abs_delta: float | None
    percent_delta: float | None
    minimum_baseline: float | None
    trigger_mode: str | None
    no_flow_threshold: None = None
    low_flow_threshold: None = None
    recovery_threshold: None = None


class FlowStateRuleOut(_OperationalRuleOutBase):
    field: Literal["debit"]
    secondary_field: None
    rule_type: Literal["flow_state"]
    no_flow_threshold: float
    low_flow_threshold: float
    recovery_threshold: float
    window_seconds: None = None
    min_points: None = None
    abs_delta: None = None
    percent_delta: None = None
    minimum_baseline: None = None
    trigger_mode: None = None


class LowFlowTssRuleOut(_OperationalRuleOutBase):
    field: Literal["debit"]
    secondary_field: Literal["tss"]
    rule_type: Literal["low_flow_tss"]
    window_seconds: None = None
    min_points: None = None
    abs_delta: None = None
    percent_delta: None = None
    minimum_baseline: None = None
    trigger_mode: None = None
    no_flow_threshold: None = None


OperationalRuleOut = Annotated[
    RapidChangeRuleOut | FlowStateRuleOut | LowFlowTssRuleOut,
    Field(discriminator="rule_type"),
]


class MonitoringThresholdOut(BaseModel):
    field: str
    warning_min: float | None
    warning_max: float | None
    danger_min: float | None
    danger_max: float | None
    reference_label: str | None
    regulation: str | None


class MonitoringConfigOut(BaseModel):
    site_uid: str
    cadence_seconds: int
    stale_after_seconds: int
    max_chart_points: int
    max_range_days: int
    updated_by_user_id: int | None
    rules: list[OperationalRuleOut]
    thresholds: list[MonitoringThresholdOut]
