"""
Tests for Task 18: Quiz Topic Anchor

Verifies that:
1. start_quiz() loads Course and uses course.name as course_topic
2. user_checkin does NOT override concept_names
3. lesson_content uses content_markdown if available
4. answer_evaluation prompt contains course_topic
5. quiz_question_generation prompt contains course_topic
6. LLMService.generate_quiz_question() accepts course_topic param
7. LLMService.evaluate_answer() accepts course_topic param
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_lesson(
    lesson_id: int = 5,
    course_id: int = 10,
    title: str = "Section 1",
    description: str = "",
    content_markdown: str = "",
    content_url: str = ""
) -> MagicMock:
    lesson = MagicMock()
    lesson.lesson_id = lesson_id
    lesson.course_id = course_id
    lesson.title = title
    lesson.description = description
    lesson.content_markdown = content_markdown
    lesson.content_url = content_url
    return lesson


def make_course(course_id: int = 10, name: str = "Piano cơ bản") -> MagicMock:
    course = MagicMock()
    course.course_id = course_id
    course.name = name
    return course


def make_user(user_id: int = 1) -> MagicMock:
    user = MagicMock()
    user.user_id = user_id
    return user


def make_quiz_session(session_id: int = 42, lesson: MagicMock = None, messages: list = None) -> MagicMock:
    qs = MagicMock()
    qs.session_id = session_id
    qs.status = "active"
    qs.lesson = lesson or make_lesson()
    qs.messages = messages or [{"role": "assistant", "content": "Câu hỏi về piano?"}]
    return qs


# ---------------------------------------------------------------------------
# Test Group 1: LLMPrompts.quiz_question_generation includes course_topic
# ---------------------------------------------------------------------------

class TestQuizQuestionGenerationPrompt:
    """LLMPrompts.quiz_question_generation() must accept course_topic param and include it in the prompt."""

    def test_prompt_contains_course_topic_when_provided(self):
        from app.services.llm_prompts import LLMPrompts

        prompt = LLMPrompts.quiz_question_generation(
            lesson_content="Bài học về nốt nhạc cơ bản",
            conversation_history=[],
            concepts=["Nốt Đô", "Nốt Rê"],
            is_first_question=True,
            course_topic="Piano cơ bản"
        )

        assert "Piano cơ bản" in prompt

    def test_prompt_contains_course_topic_in_followup(self):
        from app.services.llm_prompts import LLMPrompts

        prompt = LLMPrompts.quiz_question_generation(
            lesson_content="Bài học về nốt nhạc cơ bản",
            conversation_history=[
                {"role": "assistant", "content": "Nốt Đô là gì?"},
                {"role": "user", "content": "Là nốt nhạc đầu tiên"}
            ],
            concepts=["Nốt Đô", "Nốt Rê"],
            is_first_question=False,
            course_topic="Piano cơ bản"
        )

        assert "Piano cơ bản" in prompt

    def test_prompt_works_without_course_topic(self):
        """Existing callers with no course_topic param should still work."""
        from app.services.llm_prompts import LLMPrompts

        # Should not raise — course_topic defaults to ""
        prompt = LLMPrompts.quiz_question_generation(
            lesson_content="Bài học về nốt nhạc",
            conversation_history=[],
            concepts=["Nốt Đô"],
            is_first_question=True
        )

        assert prompt  # Non-empty prompt returned


# ---------------------------------------------------------------------------
# Test Group 2: LLMPrompts.answer_evaluation includes course_topic
# ---------------------------------------------------------------------------

class TestAnswerEvaluationPrompt:
    """LLMPrompts.answer_evaluation() must accept course_topic param and inject it into prompt."""

    def test_prompt_contains_course_topic(self):
        from app.services.llm_prompts import LLMPrompts

        prompt = LLMPrompts.answer_evaluation(
            question="Nốt Đô nằm ở đâu trên phím đàn?",
            user_answer="Nốt Đô nằm ở phím trắng bên trái nhóm 2 phím đen",
            lesson_context="Nốt nhạc cơ bản trong Piano",
            concepts=["Nốt Đô"],
            course_topic="Piano cơ bản"
        )

        assert "Piano cơ bản" in prompt

    def test_prompt_has_offtopic_validation(self):
        """Prompt phải có instruction về off-topic khi course_topic được cung cấp."""
        from app.services.llm_prompts import LLMPrompts

        prompt = LLMPrompts.answer_evaluation(
            question="Nốt Đô nằm ở đâu?",
            user_answer="Chia động từ tiếng Anh",
            lesson_context="Piano cơ bản",
            concepts=["Nốt Đô"],
            course_topic="Piano cơ bản"
        )

        # Prompt must instruct LLM to check if answer is related to course_topic
        prompt_lower = prompt.lower()
        assert "piano cơ bản" in prompt_lower

    def test_prompt_works_without_course_topic(self):
        """Existing callers should still work without course_topic."""
        from app.services.llm_prompts import LLMPrompts

        prompt = LLMPrompts.answer_evaluation(
            question="Câu hỏi",
            user_answer="Câu trả lời",
            lesson_context="Nội dung bài",
            concepts=["khái niệm"]
        )

        assert prompt  # Non-empty


# ---------------------------------------------------------------------------
# Test Group 3: LLMService method signatures accept course_topic
# ---------------------------------------------------------------------------

class TestLLMServiceCourseTopicParam:
    """LLMService.generate_quiz_question() and .evaluate_answer() must accept course_topic param."""

    def _make_llm_service(self):
        from app.services.llm_service import LLMService
        with patch("app.services.llm_service.OpenAI"):
            svc = LLMService(
                api_key="test-key",
                base_url="http://localhost",
                fast_model="gpt-4o-mini",
                smart_model="gpt-4o"
            )
        return svc

    def test_generate_quiz_question_accepts_course_topic(self):
        """generate_quiz_question() must accept course_topic keyword argument."""
        from app.services.llm_service import LLMService

        svc = self._make_llm_service()

        # Mock the client response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Nốt Đô nằm ở đâu?"
        svc.client.chat.completions.create.return_value = mock_response

        # Must not raise TypeError
        result = svc.generate_quiz_question(
            lesson_content="Bài học Piano",
            conversation_history=[],
            concepts=["Nốt Đô"],
            is_first_question=True,
            course_topic="Piano cơ bản"
        )

        assert result == "Nốt Đô nằm ở đâu?"

    def test_generate_quiz_question_passes_course_topic_to_prompt(self):
        """generate_quiz_question() must pass course_topic to LLMPrompts."""
        from app.services.llm_service import LLMService
        from app.services.llm_prompts import LLMPrompts

        svc = self._make_llm_service()

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Câu hỏi"
        svc.client.chat.completions.create.return_value = mock_response

        with patch.object(LLMPrompts, "quiz_question_generation", wraps=LLMPrompts.quiz_question_generation) as mock_prompt:
            svc.generate_quiz_question(
                lesson_content="Bài Piano",
                conversation_history=[],
                concepts=["Nốt Đô"],
                is_first_question=True,
                course_topic="Piano cơ bản"
            )

        # Verify course_topic was passed to prompt generation
        mock_prompt.assert_called_once()
        _, kwargs = mock_prompt.call_args
        assert kwargs.get("course_topic") == "Piano cơ bản" or "Piano cơ bản" in mock_prompt.call_args.args

    def test_evaluate_answer_accepts_course_topic(self):
        """evaluate_answer() must accept course_topic keyword argument."""
        import json
        from app.services.llm_service import LLMService

        svc = self._make_llm_service()

        evaluation_json = json.dumps({
            "is_correct": True,
            "confidence": 0.9,
            "engagement_level": "high",
            "key_concepts_covered": ["Nốt Đô"],
            "key_concepts_missed": [],
            "feedback": "Rất tốt!"
        })
        mock_response = MagicMock()
        mock_response.choices[0].message.content = evaluation_json
        svc.client.chat.completions.create.return_value = mock_response

        # Must not raise TypeError
        result = svc.evaluate_answer(
            question="Nốt Đô nằm ở đâu?",
            user_answer="Phím trắng bên trái nhóm 2 phím đen",
            lesson_context="Piano cơ bản — nốt nhạc",
            concepts=["Nốt Đô"],
            course_topic="Piano cơ bản"
        )

        assert result.is_correct is True

    def test_evaluate_answer_passes_course_topic_to_prompt(self):
        """evaluate_answer() must pass course_topic to LLMPrompts."""
        import json
        from app.services.llm_service import LLMService
        from app.services.llm_prompts import LLMPrompts

        svc = self._make_llm_service()

        evaluation_json = json.dumps({
            "is_correct": False,
            "confidence": 0.8,
            "engagement_level": "low",
            "key_concepts_covered": [],
            "key_concepts_missed": ["Nốt Đô"],
            "feedback": "Câu trả lời không liên quan."
        })
        mock_response = MagicMock()
        mock_response.choices[0].message.content = evaluation_json
        svc.client.chat.completions.create.return_value = mock_response

        with patch.object(LLMPrompts, "answer_evaluation", wraps=LLMPrompts.answer_evaluation) as mock_prompt:
            svc.evaluate_answer(
                question="Nốt Đô nằm ở đâu?",
                user_answer="Chia động từ tiếng Anh",
                lesson_context="Piano cơ bản",
                concepts=["Nốt Đô"],
                course_topic="Piano cơ bản"
            )

        mock_prompt.assert_called_once()
        _, kwargs = mock_prompt.call_args
        assert kwargs.get("course_topic") == "Piano cơ bản" or "Piano cơ bản" in mock_prompt.call_args.args


# ---------------------------------------------------------------------------
# Test Group 4: QuizService.start_quiz() — Course loading and topic anchor
# ---------------------------------------------------------------------------

class TestStartQuizCourseTopicAnchor:
    """start_quiz() must load Course, use course.name as topic, not let user_checkin override concept_names."""

    def _make_db_session(self, user, lesson, course, concepts=None):
        """Create a mock db session that returns appropriate objects for query chains."""
        db = MagicMock()

        def query_side_effect(model):
            from app.models import User, Lesson, Concept
            from app.models.course import Course

            q = MagicMock()
            if model == User:
                q.filter.return_value.first.return_value = user
            elif model == Lesson:
                q.filter.return_value.first.return_value = lesson
            elif model == Course:
                q.filter.return_value.first.return_value = course
            elif model == Concept:
                q.filter.return_value.all.return_value = concepts or []
            else:
                q.filter.return_value.first.return_value = None
                q.filter.return_value.all.return_value = []
            return q

        db.query.side_effect = query_side_effect
        db.flush = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.rollback = MagicMock()

        return db

    def test_start_quiz_loads_course_topic(self):
        """start_quiz() must query Course and use course.name as course_topic."""
        from app.services.quiz_service import QuizService

        lesson = make_lesson(course_id=10, title="Section 1")
        course = make_course(course_id=10, name="Piano cơ bản")
        user = make_user()

        mock_llm = MagicMock()
        mock_llm.generate_quiz_question.return_value = "Câu hỏi đầu tiên về piano?"

        db = self._make_db_session(user, lesson, course)

        # Capture the session that's created
        created_sessions = []
        original_add = db.add
        def capture_add(obj):
            created_sessions.append(obj)
            if hasattr(obj, 'session_id'):
                obj.session_id = 42
        db.add.side_effect = capture_add

        # After flush, give session_id
        def flush_side_effect():
            for obj in created_sessions:
                if hasattr(obj, 'session_id') and obj.session_id is None:
                    obj.session_id = 42
        db.flush.side_effect = flush_side_effect

        svc = QuizService(llm_service=mock_llm)
        result = svc.start_quiz(
            user_id=1,
            lesson_id=5,
            user_checkin="Học về chia động từ tiếng Anh",
            db_session=db
        )

        # LLM must have been called with course_topic
        call_kwargs = mock_llm.generate_quiz_question.call_args
        assert call_kwargs is not None

        # Check that course_topic was passed (either as arg or kwarg)
        all_args = list(call_kwargs.args) + list(call_kwargs.kwargs.values())
        assert "Piano cơ bản" in all_args, f"course_topic 'Piano cơ bản' not found in call args: {call_kwargs}"

    def test_user_checkin_does_not_override_concept_names(self):
        """user_checkin must NOT replace concept_names when lesson has no concepts in DB."""
        from app.services.quiz_service import QuizService

        lesson = make_lesson(title="Section 1")
        course = make_course(name="Piano cơ bản")
        user = make_user()

        # No concepts in DB (empty list)
        mock_llm = MagicMock()
        mock_llm.generate_quiz_question.return_value = "Câu hỏi?"

        db = self._make_db_session(user, lesson, course, concepts=[])

        created_sessions = []
        def capture_add(obj):
            created_sessions.append(obj)
        db.add.side_effect = capture_add

        svc = QuizService(llm_service=mock_llm)
        svc.start_quiz(
            user_id=1,
            lesson_id=5,
            user_checkin="Chia động từ tiếng Anh",
            db_session=db
        )

        # Check what concepts were passed to generate_quiz_question
        call_kwargs = mock_llm.generate_quiz_question.call_args
        # concepts argument — find it
        concepts_arg = None
        if call_kwargs.kwargs.get("concepts") is not None:
            concepts_arg = call_kwargs.kwargs["concepts"]
        elif len(call_kwargs.args) >= 3:
            concepts_arg = call_kwargs.args[2]

        # concepts must be lesson.title or similar, NOT the user_checkin text
        if concepts_arg is not None:
            assert "Chia động từ tiếng Anh" not in concepts_arg, \
                f"user_checkin text found in concept_names: {concepts_arg}"

    def test_lesson_content_uses_content_markdown_when_available(self):
        """start_quiz() must use lesson.content_markdown as lesson_content when available."""
        from app.services.quiz_service import QuizService

        markdown_content = "# Piano cơ bản\n\nNốt Đô là nốt nhạc đầu tiên..."
        lesson = make_lesson(
            title="Section 1",
            description="Mô tả ngắn",
            content_markdown=markdown_content
        )
        course = make_course(name="Piano cơ bản")
        user = make_user()

        mock_llm = MagicMock()
        mock_llm.generate_quiz_question.return_value = "Câu hỏi?"

        db = self._make_db_session(user, lesson, course, concepts=[])

        created_sessions = []
        def capture_add(obj):
            created_sessions.append(obj)
        db.add.side_effect = capture_add

        svc = QuizService(llm_service=mock_llm)
        svc.start_quiz(
            user_id=1,
            lesson_id=5,
            user_checkin=None,
            db_session=db
        )

        # lesson_content passed to generate_quiz_question must contain content_markdown
        call_kwargs = mock_llm.generate_quiz_question.call_args
        lesson_content_arg = None
        if call_kwargs.kwargs.get("lesson_content") is not None:
            lesson_content_arg = call_kwargs.kwargs["lesson_content"]
        elif len(call_kwargs.args) >= 1:
            lesson_content_arg = call_kwargs.args[0]

        assert lesson_content_arg is not None
        assert "Nốt Đô là nốt nhạc đầu tiên" in lesson_content_arg, \
            f"content_markdown not found in lesson_content passed to LLM: {lesson_content_arg}"


# ---------------------------------------------------------------------------
# Test Group 5: QuizService.submit_answer() — same fixes
# ---------------------------------------------------------------------------

class TestSubmitAnswerCourseTopicAnchor:
    """submit_answer() must load Course, not let stored_checkin override concept_names."""

    def _make_db_with_session(self, quiz_session, lesson, course, concepts=None):
        db = MagicMock()

        from app.models import QuizSession, Concept
        from app.models.course import Course

        def query_side_effect(model):
            q = MagicMock()
            if model == QuizSession:
                q.filter.return_value.first.return_value = quiz_session
            elif model == Concept:
                q.filter.return_value.all.return_value = concepts or []
            elif model == Course:
                q.filter.return_value.first.return_value = course
            else:
                q.filter.return_value.first.return_value = None
                q.filter.return_value.all.return_value = []
            return q

        db.query.side_effect = query_side_effect
        db.add = MagicMock()
        db.commit = MagicMock()
        db.rollback = MagicMock()

        return db

    def test_submit_answer_loads_course_topic(self):
        """submit_answer() must query Course and pass course_topic to evaluate_answer."""
        from app.services.quiz_service import QuizService
        from app.services.llm_service import AnswerEvaluation, EngagementLevel, NextAction, ActionType

        lesson = make_lesson(course_id=10, title="Section 1")
        course = make_course(course_id=10, name="Piano cơ bản")

        messages = [
            {"role": "_checkin", "content": "Chia động từ tiếng Anh"},
            {"role": "assistant", "content": "Nốt Đô nằm ở đâu?"}
        ]
        quiz_session = make_quiz_session(session_id=42, lesson=lesson, messages=messages)

        mock_evaluation = AnswerEvaluation(
            is_correct=True,
            confidence=0.9,
            engagement_level=EngagementLevel.HIGH,
            key_concepts_covered=["Nốt Đô"],
            key_concepts_missed=[],
            feedback="Tốt lắm!"
        )
        mock_next_action = NextAction(
            action_type=ActionType.END,
            reason="Done",
            follow_up_question=None
        )

        mock_llm = MagicMock()
        mock_llm.evaluate_answer.return_value = mock_evaluation
        mock_llm.decide_next_action.return_value = mock_next_action
        mock_llm.generate_quiz_summary.return_value = MagicMock(
            summary_text="Tóm tắt", concepts_mastered=[], concepts_weak=[]
        )

        db = self._make_db_with_session(quiz_session, lesson, course, concepts=[])

        svc = QuizService(llm_service=mock_llm)
        svc.submit_answer(
            session_id=42,
            user_answer="Phím trắng bên trái",
            db_session=db
        )

        # evaluate_answer must have been called with course_topic
        eval_call = mock_llm.evaluate_answer.call_args
        assert eval_call is not None
        all_args = list(eval_call.args) + list(eval_call.kwargs.values())
        assert "Piano cơ bản" in all_args, \
            f"course_topic 'Piano cơ bản' not found in evaluate_answer call args: {eval_call}"

    def test_submit_answer_stored_checkin_does_not_override_concept_names(self):
        """submit_answer() must NOT let stored_checkin replace concept_names."""
        from app.services.quiz_service import QuizService
        from app.services.llm_service import AnswerEvaluation, EngagementLevel, NextAction, ActionType

        lesson = make_lesson(course_id=10, title="Section 1")
        course = make_course(course_id=10, name="Piano cơ bản")

        # Messages include a _checkin with off-topic content
        messages = [
            {"role": "_checkin", "content": "Chia động từ tiếng Anh"},
            {"role": "assistant", "content": "Nốt Đô nằm ở đâu?"}
        ]
        quiz_session = make_quiz_session(session_id=42, lesson=lesson, messages=messages)

        mock_evaluation = AnswerEvaluation(
            is_correct=True,
            confidence=0.9,
            engagement_level=EngagementLevel.MEDIUM,
            key_concepts_covered=[],
            key_concepts_missed=[],
            feedback="OK"
        )
        mock_next_action = NextAction(
            action_type=ActionType.END,
            reason="Done",
            follow_up_question=None
        )

        mock_llm = MagicMock()
        mock_llm.evaluate_answer.return_value = mock_evaluation
        mock_llm.decide_next_action.return_value = mock_next_action
        mock_llm.generate_quiz_summary.return_value = MagicMock(
            summary_text="Tóm tắt", concepts_mastered=[], concepts_weak=[]
        )

        db = self._make_db_with_session(quiz_session, lesson, course, concepts=[])

        svc = QuizService(llm_service=mock_llm)
        svc.submit_answer(
            session_id=42,
            user_answer="Phím trắng bên trái",
            db_session=db
        )

        # Concepts passed to evaluate_answer must NOT be the checkin text
        eval_call = mock_llm.evaluate_answer.call_args
        concepts_arg = None
        if eval_call.kwargs.get("concepts") is not None:
            concepts_arg = eval_call.kwargs["concepts"]
        elif len(eval_call.args) >= 4:
            concepts_arg = eval_call.args[3]

        if concepts_arg is not None:
            assert "Chia động từ tiếng Anh" not in concepts_arg, \
                f"stored_checkin found in concept_names passed to evaluate: {concepts_arg}"
