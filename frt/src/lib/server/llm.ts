import OpenAI from 'openai';

interface LLMConfig {
  baseURL: string;
  apiKey?: string;
  model: string;
  displayName: string;
}

const providerConfigs: Record<string, LLMConfig> = {
  qwen: {
    baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1/',
    apiKey: process.env.DASHSCOPE_API_KEY,
    model: 'qwen-plus',
    displayName: 'Qwen Plus'
  },
  grok: {
    baseURL: 'https://api.x.ai/v1/',
    apiKey: process.env.GROK_API_KEY,
    model: 'grok-code-fast-1',
    displayName: 'Grok Code Fast'
  },
  glm: {
    baseURL: 'https://open.bigmodel.cn/api/paas/v4/',
    apiKey: process.env.Z_API_KEY,
    model: 'glm-4.5',
    displayName: 'GLM 4.5'
  },
  ollama: {
    baseURL: process.env.OLLAMA_BASE_URL || 'http://localhost:11434/v1/',
    model: 'llama3.1',
    displayName: 'Ollama Llama 3.1'
  }
};

const SYSTEM_PROMPT = 'You are a professional subtitle generator for videos. Your task is to create natural, well-timed subtitles based on the given content.\n\n' +
'CRITICAL PUNCTUATION REQUIREMENTS:\n' +
'1. RESTRICTED PUNCTUATION: You may ONLY use these four Chinese punctuation marks:\n' +
'   - Chinese comma: ，\n' +
'   - Chinese period: 。\n' +
'   - Chinese question mark: ？\n' +
'   - Chinese exclamation mark: ！\n' +
'2. FORBIDDEN PUNCTUATION: DO NOT use any other punctuation marks, including:\n' +
'   - Em dashes: —— (absolutely forbidden)\n' +
'   - Semicolons: ；；\n' +
'   - Colons: ：：\n' +
'   - Parentheses: ()（）\n' +
'   - Brackets: []【】\n' +
'   - Quotes: ""\'\'""\'\'\n' +
'   - Enumeration commas: 、\n' +
'   - English punctuation: .,!?:;\'"`()[ ]<>\n' +
'   - Any other special characters or symbols\n\n' +
'IMPORTANT REQUIREMENTS:\n' +
'1. Natural Breaks: Break content at natural speaking pauses, commas, periods, or logical stops\n' +
'2. Complete Thoughts: Don\'t break in the middle of phrases or ideas\n' +
'3. Use Rich Expressions: Add appropriate modifiers, connecting words, and complete clause structures\n' +
'4. One Line: Each subtitle should be a single line (no line breaks within subtitles)\n' +
'5. CRITICAL: Include proper punctuation (commas, periods, question marks, exclamation marks) for natural TTS speech synthesis\n\n' +
'FORMAT REQUIREMENTS:\n' +
'- Mobile Optimization: Keep text concise to ensure readability on small mobile screens\n' +
'- Sentence Structure: Combine related concepts into complete, coherent sentences\n' +
'- Natural Flow: Use rich expressions with appropriate modifiers and connecting words\n' +
'- Complete Clauses: Ensure each sentence contains complete meaning expression\n' +
'- End with Period: Every sentence must end with a Chinese period (。)\n' +
'- One Sentence Per Line: Each line should contain one complete sentence\n' +
'- Width Constraint: Ensure text fits within mobile screen width (approximately 20-25 characters maximum)\n\n' +
'TONE REQUIREMENTS:\n' +
'1. Marketing Language: Use persuasive language to enhance product appeal\n' +
'2. Concise and Powerful: Keep language clean and impactful for high-end technical product promotion\n\n' +
'FORMAT:\n' +
'- Return each subtitle on a separate line\n' +
'- No numbering, no extra formatting\n' +
'- Clean, readable text suitable for TTS and video display\n\n' +
'Examples of good subtitles:\n' +
'"NVIDIA 5090液冷一体机"\n' +
'"正通过AI技术改变我们的生活"\n' +
'"超强AI计算能力为您带来"\n' +
'"卓越的性能提升和高效的深度学习体验"\n' +
'"创新液冷散热系统保持工作环境"\n' +
'"安静无扰，温度控制精准稳定"\n' +
'"RTX 5090显卡技术支持"\n' +
'"大型AI模型运行，处理复杂任务轻松高效"\n' +
'"开箱即用"\n' +
'"集成管理采用软硬件一体化设计"\n' +
'"即插即用便捷体验"';

export class LLMManager {
  private getProviderConfig(provider: string): LLMConfig {
    const config = providerConfigs[provider];
    if (!config) {
      throw new Error(`Unsupported LLM provider: ${provider}`);
    }

    // Validate API key for providers that require it
    if (provider !== 'ollama' && !config.apiKey) {
      throw new Error(`API key not found for ${config.displayName}. Please set ${provider.toUpperCase()}_API_KEY in environment variables.`);
    }

    return config;
  }

  async generateSubtitles(
    news?: string,
    business?: string,
    commonPrompt?: string,
    provider: string = 'qwen'
  ): Promise<string[]> {
    try {
      console.log(`🤖 [LLM] Generating subtitles using ${provider}`);

      const config = this.getProviderConfig(provider);

      // Build prompt content (reproducing +server.ts logic)
      const promptContent = this.buildPromptContent(news, business, commonPrompt);

      // Build user message with additional instructions (reproducing llm_module.py logic)
      const userContent = `${promptContent}

IMPORTANT: When generating subtitles for the above content, you MUST follow these punctuation rules:

- ONLY use: Chinese comma (，), Chinese period (。), Chinese question mark (？), Chinese exclamation mark (！)
- NEVER use: em dashes (——), semicolons (；), colons (：), parentheses, quotes, enumeration commas (、), or any English punctuation
- NO other special characters or symbols allowed

Generate clean, natural subtitles using only the allowed punctuation marks.`;

      // Create OpenAI client
      const client = new OpenAI({
        baseURL: config.baseURL,
        apiKey: config.apiKey || 'ollama' // Ollama doesn't need API key
      });

      console.log(`🔗 [LLM] Calling ${config.displayName} API at ${config.baseURL}`);

      console.log('SYSTEM:', SYSTEM_PROMPT);
      console.log('User:', userContent);

      // Call LLM API
      const response = await client.chat.completions.create({
        model: config.model,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: userContent }
        ],
        temperature: 0.7,
        max_tokens: 2000
      });

      console.log(`✅ [LLM] Received response from ${config.displayName}`);

      // Parse and process subtitles
      const subtitles = this.parseSubtitlesResponse(response.choices[0].message.content);

      console.log(`📝 [LLM] Generated ${subtitles.length} subtitles`);
      return subtitles;

    } catch (error) {
      console.error(`❌ [LLM] Subtitle generation failed:`, error);

      // Provide helpful error messages
      if (error instanceof Error) {
        const errorMessage = error.message.toLowerCase();

        if (errorMessage.includes('api_key') || errorMessage.includes('auth') || errorMessage.includes('unauthorized')) {
          throw new Error(`API key issue for ${provider}. Please check your ${provider.toUpperCase()}_API_KEY in .env file`);
        } else if (errorMessage.includes('rate') || errorMessage.includes('limit')) {
          throw new Error(`Rate limit exceeded for ${provider}. Please try again later.`);
        } else if (errorMessage.includes('connection') || errorMessage.includes('network')) {
          throw new Error(`Network connection issue. Please check your internet connection and ${provider} service status.`);
        } else if (errorMessage.includes('model_not_found') || errorMessage.includes('does not exist')) {
          throw new Error(`Model ${providerConfigs[provider]?.model} not available for ${provider}.`);
        }
      }

      throw error;
    }
  }

  private buildPromptContent(news?: string, business?: string, commonPrompt?: string): string {
    // Reproduce the exact logic from +server.ts lines 55-93
    let txt = '';
    const hasNews = news?.trim();
    const hasBusiness = business?.trim();
    const hasCommon = commonPrompt?.trim();

    if (hasNews) {
      txt += '\n<news>\n' + hasNews + '\n</news>\n';
    }
    if (hasBusiness) {
      txt += '\n\n<business>\n' + hasBusiness + '\n</business>\n';
    }

    txt += "\n<instruct>\n"
    if (hasCommon) {
      txt += hasCommon;
    }

    if (hasNews && hasBusiness) {
      txt += '努力找到news和business的相关性。\n请先根据 news 的内容生成科技新闻阐述字幕\n再把 business 的内容生成为口播字幕\nnews的内容在前， business的内容在后， 中间前后两部份自然衔接过渡';
    } else if (hasNews) {
      txt += '请根据 NEWS 的内容生成科技新闻口播字幕';
    } else if (hasBusiness) {
      txt += '请根据 BUSINESS 的内容生成口播字幕';
    }
    txt += "\n</instruct>"

    return txt;
  }

  private parseSubtitlesResponse(content: string | null): string[] {
    if (!content) {
      throw new Error('No content received from LLM');
    }

    // Parse subtitles from response (reproducing Python logic)
    const rawSubtitles = content
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0);

    if (rawSubtitles.length === 0) {
      throw new Error('No subtitles generated');
    }

    // Return voice subtitles (with punctuation) as they are used for the final output
    return rawSubtitles;
  }
}
