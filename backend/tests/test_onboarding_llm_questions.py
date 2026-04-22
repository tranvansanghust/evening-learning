"""
Tests for onboarding flow với LLM-generated assessment questions.

Tests:
- Bước course_input → gọi LLM gen questions → hiển thị q1 từ LLM (không hardcode)
- Bước q1 → hiển thị q2_if_no khi answer = "never"
- Bước q1 → hiển thị q2_if_yes khi answer = "yes"
- LLM lỗi → fallback về câu hỏi generic, onboarding vẫn tiếp tục
- Q1 text không chứa "web app" khi topic là "Machine Learning"
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_message(text: str, telegram_id: str = "111") -> MagicMock:
    """Tạo fake aiogram Message."""
    msg = MagicMock()
    msg.text = text
    msg.from_user.id = int(telegram_id)
    msg.from_user.username = f"user_{telegram_id}"
    msg.answer = AsyncMock()
    return msg


def make_onboarding_state(step: str, q1_text: str = None, q2_text_if_no: str = None, q2_text_if_yes: str = None) -> MagicMock:
    """Tạo fake OnboardingState."""
    state = MagicMock()
    state.current_step = step
    state.q1_text = q1_text
    state.q2_text_if_no = q2_text_if_no
    state.q2_text_if_yes = q2_text_if_yes
    state.course_topic = "Machine Learning"
    return state


class TestCourseInputStepWithLLM:
    """Bước course_input → gọi LLM → hiển thị q1 từ LLM."""

    @pytest.mark.asyncio
    async def test_course_input_displays_llm_q1(self):
        """Bước course_input: câu hỏi Q1 hiển thị từ LLM, không hardcode."""
        from app.routers.telegram_handlers import _handle_onboarding_step

        msg = make_message("Machine Learning")
        ob_state = make_onboarding_state("course_input")

        onboarding_service = MagicMock()
        onboarding_service.update_onboarding_state = MagicMock()

        llm_questions = {
            "q1": "Bạn đã từng học Machine Learning chưa?",
            "q2_if_no": "Bạn đã biết Python và toán cơ bản chưa?",
            "q2_if_yes": "Bạn đã train model thực tế chưa?",
        }

        with patch("app.routers.telegram_handlers.LLMAssessmentGenerator") as MockGen:
            mock_gen_instance = MagicMock()
            mock_gen_instance.generate_assessment_questions.return_value = llm_questions
            MockGen.return_value = mock_gen_instance

            with patch("app.routers.telegram_handlers.LLMService"):
                with patch("app.routers.telegram_handlers.settings"):
                    await _handle_onboarding_step(msg, "Machine Learning", 1, ob_state, onboarding_service)

        # Câu hỏi gửi đến user phải là q1 từ LLM
        msg.answer.assert_called_once()
        call_args = msg.answer.call_args
        response_text = call_args.args[0] if call_args.args else str(call_args)
        assert "Machine Learning" in response_text, (
            f"Q1 phải chứa topic 'Machine Learning', nhưng nhận được: {response_text}"
        )
        assert "web app" not in response_text.lower(), (
            f"Q1 không được chứa 'web app' khi topic là Machine Learning"
        )

    @pytest.mark.asyncio
    async def test_course_input_saves_questions_to_state(self):
        """Bước course_input: q1_text, q2_text_if_no, q2_text_if_yes phải được lưu vào state."""
        from app.routers.telegram_handlers import _handle_onboarding_step

        msg = make_message("Python cơ bản")
        ob_state = make_onboarding_state("course_input")

        onboarding_service = MagicMock()
        onboarding_service.update_onboarding_state = MagicMock()

        llm_questions = {
            "q1": "Bạn đã từng học Python chưa?",
            "q2_if_no": "Bạn đã biết lập trình cơ bản chưa?",
            "q2_if_yes": "Bạn đã xây dựng dự án Python chưa?",
        }

        with patch("app.routers.telegram_handlers.LLMAssessmentGenerator") as MockGen:
            mock_gen_instance = MagicMock()
            mock_gen_instance.generate_assessment_questions.return_value = llm_questions
            MockGen.return_value = mock_gen_instance

            with patch("app.routers.telegram_handlers.LLMService"):
                with patch("app.routers.telegram_handlers.settings"):
                    await _handle_onboarding_step(msg, "Python cơ bản", 1, ob_state, onboarding_service)

        # Kiểm tra update_onboarding_state được gọi với q1_text/q2_text
        calls = onboarding_service.update_onboarding_state.call_args_list
        # Phải có ít nhất 1 call với q1_text
        q1_text_saved = any(
            call.kwargs.get("q1_text") == llm_questions["q1"]
            for call in calls
        )
        assert q1_text_saved, f"q1_text phải được lưu vào state. Calls: {calls}"

    @pytest.mark.asyncio
    async def test_course_input_llm_failure_fallback(self):
        """LLM lỗi khi generate questions → fallback về câu hỏi generic, không crash."""
        from app.routers.telegram_handlers import _handle_onboarding_step

        msg = make_message("DevOps")
        ob_state = make_onboarding_state("course_input")

        onboarding_service = MagicMock()
        onboarding_service.update_onboarding_state = MagicMock()

        with patch("app.routers.telegram_handlers.LLMAssessmentGenerator") as MockGen:
            mock_gen_instance = MagicMock()
            # LLMAssessmentGenerator.generate_assessment_questions sẽ fallback nội bộ
            # nhưng LLMService constructor có thể raise
            mock_gen_instance.generate_assessment_questions.return_value = {
                "q1": "Bạn đã có kinh nghiệm với DevOps chưa?",
                "q2_if_no": "Bạn đã có nền tảng lập trình cơ bản chưa?",
                "q2_if_yes": "Bạn đã từng làm dự án thực tế với DevOps chưa?",
            }
            MockGen.return_value = mock_gen_instance

            with patch("app.routers.telegram_handlers.LLMService") as MockLLM:
                MockLLM.side_effect = Exception("LLM init failed")
                with patch("app.routers.telegram_handlers.settings"):
                    # Không được raise — phải xử lý gracefully
                    await _handle_onboarding_step(msg, "DevOps", 1, ob_state, onboarding_service)

        # Bot vẫn phải trả lời cho user (fallback question)
        msg.answer.assert_called_once()


class TestQ1StepWithLLMQuestions:
    """Bước q1 → dùng q2_text từ state thay vì hardcode."""

    @pytest.mark.asyncio
    async def test_q1_never_displays_q2_if_no_from_state(self):
        """Q1 = 'Chưa' → hiển thị q2_text_if_no từ state."""
        from app.routers.telegram_handlers import _handle_onboarding_step

        q2_from_llm = "Bạn đã biết Python và toán cơ bản chưa?"
        ob_state = make_onboarding_state(
            step="q1",
            q2_text_if_no=q2_from_llm,
            q2_text_if_yes="Bạn đã train model thực tế chưa?",
        )

        msg = make_message("Chưa")
        onboarding_service = MagicMock()
        onboarding_service.update_onboarding_state = MagicMock()
        onboarding_service.get_onboarding_state = MagicMock(return_value=ob_state)

        await _handle_onboarding_step(msg, "Chưa", 1, ob_state, onboarding_service)

        msg.answer.assert_called_once()
        response_text = msg.answer.call_args.args[0]
        assert response_text == q2_from_llm, (
            f"Q2 phải là '{q2_from_llm}' (từ LLM), nhưng nhận được: '{response_text}'"
        )

    @pytest.mark.asyncio
    async def test_q1_yes_displays_q2_if_yes_from_state(self):
        """Q1 = 'Rồi' → hiển thị q2_text_if_yes từ state."""
        from app.routers.telegram_handlers import _handle_onboarding_step

        q2_from_llm = "Bạn đã train model thực tế với scikit-learn chưa?"
        ob_state = make_onboarding_state(
            step="q1",
            q2_text_if_no="Bạn đã biết Python chưa?",
            q2_text_if_yes=q2_from_llm,
        )

        msg = make_message("Rồi")
        onboarding_service = MagicMock()
        onboarding_service.update_onboarding_state = MagicMock()
        onboarding_service.get_onboarding_state = MagicMock(return_value=ob_state)

        await _handle_onboarding_step(msg, "Rồi", 1, ob_state, onboarding_service)

        msg.answer.assert_called_once()
        response_text = msg.answer.call_args.args[0]
        assert response_text == q2_from_llm, (
            f"Q2 phải là '{q2_from_llm}' (từ LLM), nhưng nhận được: '{response_text}'"
        )

    @pytest.mark.asyncio
    async def test_q1_fallback_when_no_q2_text_in_state(self):
        """q2_text_if_no không có trong state → dùng fallback generic."""
        from app.routers.telegram_handlers import _handle_onboarding_step

        ob_state = make_onboarding_state(
            step="q1",
            q2_text_if_no=None,  # Chưa được lưu
            q2_text_if_yes=None,
        )

        msg = make_message("Chưa bao giờ")
        onboarding_service = MagicMock()
        onboarding_service.update_onboarding_state = MagicMock()
        onboarding_service.get_onboarding_state = MagicMock(return_value=ob_state)

        # Không được crash dù không có q2_text trong state
        await _handle_onboarding_step(msg, "Chưa bao giờ", 1, ob_state, onboarding_service)

        msg.answer.assert_called_once()
        response_text = msg.answer.call_args.args[0]
        assert response_text  # Phải trả về something

    @pytest.mark.asyncio
    async def test_q1_not_hardcoded_html_css(self):
        """Q2 không được hardcode 'HTML/CSS' khi topic là Machine Learning."""
        from app.routers.telegram_handlers import _handle_onboarding_step

        ob_state = make_onboarding_state(
            step="q1",
            q2_text_if_no="Bạn đã biết Python và toán cơ bản chưa?",
            q2_text_if_yes="Bạn đã train model thực tế chưa?",
        )
        ob_state.course_topic = "Machine Learning"

        msg = make_message("Chưa")
        onboarding_service = MagicMock()
        onboarding_service.update_onboarding_state = MagicMock()
        onboarding_service.get_onboarding_state = MagicMock(return_value=ob_state)

        await _handle_onboarding_step(msg, "Chưa", 1, ob_state, onboarding_service)

        response_text = msg.answer.call_args.args[0]
        assert "HTML/CSS" not in response_text, (
            f"Q2 không được chứa 'HTML/CSS' khi topic là Machine Learning"
        )


class TestAssessLevelUnchanged:
    """assess_level() vẫn hoạt động bình thường (không thay đổi)."""

    def test_assess_level_never_no_is_level_0(self):
        from unittest.mock import MagicMock
        from app.services.onboarding_service import OnboardingService
        db = MagicMock()
        service = OnboardingService(db)
        assert service.assess_level("never", "no") == 0

    def test_assess_level_never_yes_is_level_1(self):
        from app.services.onboarding_service import OnboardingService
        db = MagicMock()
        service = OnboardingService(db)
        assert service.assess_level("never", "yes") == 1

    def test_assess_level_yes_no_is_level_2(self):
        from app.services.onboarding_service import OnboardingService
        db = MagicMock()
        service = OnboardingService(db)
        assert service.assess_level("yes", "no") == 2

    def test_assess_level_yes_yes_is_level_3(self):
        from app.services.onboarding_service import OnboardingService
        db = MagicMock()
        service = OnboardingService(db)
        assert service.assess_level("yes", "yes") == 3
