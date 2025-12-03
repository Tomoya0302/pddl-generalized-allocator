class CodmapPlannerError(Exception):
    """共通の基底例外"""

class PDDLParseError(CodmapPlannerError):
    pass

class ModelBuildError(CodmapPlannerError):
    pass
