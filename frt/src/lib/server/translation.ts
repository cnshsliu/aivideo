import { Agent } from './Agent';

interface TranslationRequest {
  content: string;
  sourceLanguage: string;
  targetLanguage: string;
}

interface TranslationResult {
  translatedContent: string;
  confidence: number;
  alternatives?: string[];
}

export class TranslationService {
  private agent: Agent;

  constructor() {
    this.agent = new Agent('qwen3coder'); // Use the configured LLM
  }

  async translate(request: TranslationRequest): Promise<TranslationResult> {
    const { content, sourceLanguage, targetLanguage } = request;

    if (!content || !content.trim()) {
      throw new Error('Content is required for translation');
    }

    const prompt = `Please translate the following text from ${sourceLanguage} to ${targetLanguage}. Provide only the translated text without any additional explanations or formatting:

${content}`;

    try {
      const response = await this.agent.chat(prompt);

      // For now, return basic result structure
      // In a real implementation, you might parse confidence from the response
      return {
        translatedContent: response.response.trim(),
        confidence: 0.9, // Placeholder confidence score
        alternatives: [] // Could be populated with alternative translations
      };
    } catch (error) {
      console.error('Translation service error:', error);
      throw new Error(`Translation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}
