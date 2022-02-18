import logging
from datetime import datetime

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from superset.db_engine_specs.base import BaseEngineSpec
from superset.db_engine_specs.exceptions import SupersetDBAPIDatabaseError
from superset.utils import core as utils

from click_alchemy import driver_name

if TYPE_CHECKING:
    from superset.models.core import Database

logger = logging.getLogger(__name__)


class ClickHouseBetaEngineSpec(BaseEngineSpec):
    engine = driver_name
    engine_name = "ClickHouse Official"

    time_secondary_columns = True
    time_groupby_inline = True

    _time_grain_expressions = {
        None: "{col}",
        "PT1M": "toStartOfMinute(toDateTime({col}))",
        "PT5M": "toStartOfFiveMinutes(intDiv(toUInt32(toDateTime({col})), 300)*300)",
        "PT10M": "toStartOfTenMinutes(intDiv(toUInt32(toDateTime({col})), 600)*600)",
        "PT15M": "toStartOfFifteenMinutes(intDiv(toUInt32(toDateTime({col})), 900)*900)",
        "PT30M": "toDateTime(intDiv(toUInt32(toDateTime({col})), 1800)*1800)",
        "PT1H": "toStartOfHour(toDateTime({col}))",
        "P1D": "toStartOfDay(toDateTime({col}))",
        "P1W": "toMonday(toDateTime({col}))",
        "P1M": "toStartOfMonth(toDateTime({col}))",
        "P3M": "toStartOfQuarter(toDateTime({col}))",
        "P1Y": "toStartOfYear(toDateTime({col}))",
    }

    _function_names = None

    @classmethod
    def epoch_to_dttm(cls) -> str:
        return '{col}'

    @classmethod
    def get_dbapi_exception_mapping(cls) -> Dict[Type[Exception], Type[Exception]]:
        return {}

    @classmethod
    def get_dbapi_mapped_exception(cls, exception: Exception) -> Exception:
        new_exception = cls.get_dbapi_exception_mapping().get(type(exception))
        if new_exception == SupersetDBAPIDatabaseError:
            return SupersetDBAPIDatabaseError("Connection failed")
        if not new_exception:
            return exception
        return new_exception(str(exception))

    @classmethod
    def convert_dttm(
        cls, target_type: str, dttm: datetime, db_extra: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        tt = target_type.upper()
        if tt == utils.TemporalType.DATE:
            return f"toDate('{dttm.date().isoformat()}')"
        if tt == utils.TemporalType.DATETIME:
            return f"""toDateTime('{dttm.isoformat(sep=" ", timespec="seconds")}')"""
        return None

    @classmethod
    def get_function_names(cls, database: 'Database') -> List[str]:
        if cls._function_names:
            return cls._function_names
        try:
            names = database.get_df('SELECT name FROM system.functions')['name'].tolist()
            cls._function_names = names
            return names
        except Exception as ex:  # pylint: disable=broad-except
            logger.error('Error retrieving system.functions', str(ex), exc_info=True)
            return []