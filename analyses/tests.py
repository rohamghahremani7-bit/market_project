from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import PromptTemplate
from .services import LANGUAGE_INSTRUCTIONS, build_effective_system_prompt


class PromptTemplateTests(TestCase):
    def test_bilingual_instruction_is_added_to_system_prompt(self):
        template = PromptTemplate(
            key='test-bilingual',
            purpose='price_action',
            title='پرامپت آزمایشی',
            system_prompt='Analyze the supplied candles only.',
            output_language=PromptTemplate.OutputLanguage.BILINGUAL,
        )
        result = build_effective_system_prompt(template)
        self.assertIn('فارسی', result)
        self.assertIn('English', result)
        self.assertIn('Analyze the supplied candles only.', result)

    def test_english_instruction_is_added(self):
        template = PromptTemplate(
            key='test-english',
            purpose='price_action',
            title='English prompt',
            system_prompt='Analyze the supplied candles only.',
            output_language=PromptTemplate.OutputLanguage.ENGLISH,
        )
        result = build_effective_system_prompt(template)
        self.assertIn(LANGUAGE_INSTRUCTIONS['en'], result)

    def test_blank_system_prompt_is_rejected(self):
        template = PromptTemplate(
            key='test-empty',
            purpose='price_action',
            title='Empty prompt',
            system_prompt='   ',
        )
        with self.assertRaises(ValidationError):
            template.full_clean()
