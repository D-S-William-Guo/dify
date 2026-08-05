from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock, call

import pytest

from models.trigger import WorkflowSchedulePlan
from schedule import workflow_schedule_task


def test_process_schedules_dispatches_tasks_without_group_result(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    schedules = [
        cast(
            WorkflowSchedulePlan,
            SimpleNamespace(id="schedule-1", cron_expression="* * * * *", timezone="UTC", next_run_at=None),
        ),
        cast(
            WorkflowSchedulePlan,
            SimpleNamespace(id="schedule-2", cron_expression="0 * * * *", timezone="UTC", next_run_at=None),
        ),
    ]
    next_run_at = datetime(2026, 8, 4, 4, 0, tzinfo=UTC)
    producer = Mock(name="producer")
    session = Mock(name="session")
    schedule_task = Mock(name="run_schedule_trigger")
    group_factory = Mock(name="group")

    monkeypatch.setattr(workflow_schedule_task, "calculate_next_run_at", Mock(return_value=next_run_at))
    monkeypatch.setattr(workflow_schedule_task, "run_schedule_trigger", schedule_task)
    monkeypatch.setattr(workflow_schedule_task, "group", group_factory, raising=False)

    # Act
    dispatched_count = workflow_schedule_task._process_schedules(session, schedules, producer)

    # Assert
    assert dispatched_count == 2
    assert [schedule.next_run_at for schedule in schedules] == [next_run_at, next_run_at]
    schedule_task.apply_async.assert_has_calls(
        [
            call(args=("schedule-1",), producer=producer, ignore_result=True),
            call(args=("schedule-2",), producer=producer, ignore_result=True),
        ]
    )
    assert schedule_task.apply_async.call_count == 2
    group_factory.assert_not_called()
    session.commit.assert_called_once_with()
