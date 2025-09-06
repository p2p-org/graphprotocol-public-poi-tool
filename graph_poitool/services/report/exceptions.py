class ReportServiceError(Exception):
    """Base exception."""


class ReportServiceEBORequiredError(ReportServiceError):
    pass


class ReportServiceInvalidSubgraphError(ReportServiceError):
    pass
