import re
from datetime import datetime
from uuid import uuid4

from tlvflow.domain.enums import ReportStatus


class VehicleReport:
    def __init__(
        self,
        user_id: str,
        vehicle_id: str,
        submission_time: datetime,
        image_url: str,
        description: str,
    ):
        # Protected attributes
        self._report_id: str = uuid4().hex
        self._user_id: str = user_id
        self._vehicle_id: str = vehicle_id

        # Private attributes
        self.__submission_time: datetime = submission_time
        self.__image_url: str = image_url
        self.__description: str = description
        self.__status: ReportStatus = ReportStatus.SUBMITTED

    def verify_damage(self) -> bool:
        self.__status = ReportStatus.UNDER_REVIEW
        # As we do not have the tools to review the photo and analyze a vehicle's damage, a mock of such a test's result is used.
        mock_ai_validation_result = True

        # Review for a valid image URL structure
        img_url_pattern = r"^https?://.*\.(?:png|jpg|jpeg|gif|bmp)$"

        if (
            re.match(img_url_pattern, self.__image_url, re.IGNORECASE) is None
            or not mock_ai_validation_result
        ):
            self.__status = ReportStatus.REJECTED
            return False

        self.__status = ReportStatus.VERIFIED
        return True

    def submit_report(self) -> None:
        self.__status = ReportStatus.SUBMITTED
