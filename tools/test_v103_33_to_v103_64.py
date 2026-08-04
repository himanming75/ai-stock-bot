import tempfile,unittest
from datetime import date
from pathlib import Path

from multi_day_scheduler.calendar import (
    is_trading_day,next_trading_day,trading_days
)
from multi_day_scheduler.session import build_session,advance_session
from multi_day_scheduler.queue import build_queue,queue_summary
from multi_day_scheduler.dedup import detect_duplicate_sessions
from multi_day_scheduler.checkpoint import save_checkpoint,resume_checkpoint
from multi_day_scheduler.state import resolve_scheduler_state
from multi_day_scheduler.engine import evaluate

class Tests(unittest.TestCase):
    def test_weekend(self):
        self.assertFalse(is_trading_day(date(2026,8,1),{}))

    def test_holiday(self):
        self.assertFalse(is_trading_day(date(2026,12,25),{}))

    def test_next_trading_day(self):
        value=next_trading_day(date(2026,8,1),{})
        self.assertEqual(value.isoformat(),"2026-08-03")

    def test_trading_days(self):
        value=trading_days(date(2026,8,1),3,{})
        self.assertEqual(
            [x.isoformat() for x in value],
            ["2026-08-03","2026-08-04","2026-08-05"],
        )

    def test_session(self):
        session=build_session("2026-08-03","cycle")
        advanced=advance_session(session)
        self.assertEqual(advanced["state"],"PREOPEN")

    def test_queue(self):
        queue=build_queue(
            ["2026-08-03","2026-08-04"],
            "cycle",
        )
        self.assertEqual(queue_summary(queue)["queued_count"],2)

    def test_duplicate(self):
        queue=build_queue(["2026-08-03"],"cycle")
        session=queue["sessions"][0]
        value=detect_duplicate_sessions(
            queue["sessions"],
            [{"session_key":session["session_key"],"state":"COMPLETE"}],
        )
        self.assertEqual(value["duplicate_count"],1)

    def test_checkpoint_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"checkpoint.json"
            queue=build_queue(["2026-08-03"],"cycle")
            saved=save_checkpoint(path,"scheduler",queue)
            resumed=resume_checkpoint(path)
            self.assertTrue(resumed["resumable"])
            self.assertEqual(saved["generation"],1)

    def test_state_ready(self):
        value=resolve_scheduler_state(
            {"state":"AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL"},
            {"session_count":2},
            {"passed":True},
        )
        self.assertEqual(value["state"],"MULTI_DAY_SCHEDULER_READY")

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            result=evaluate(
                Path(temp),
                start_date="2026-08-03",
                session_count=2,
            )
            self.assertEqual(
                result["state"],
                "MULTI_DAY_SCHEDULER_SOURCE_REQUIRED",
            )

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            result=evaluate(
                Path(temp),
                start_date="2026-08-03",
                session_count=2,
            )
            self.assertEqual(result["actual_orders_submitted"],0)

if __name__=="__main__":
    unittest.main()
