import OpenAI from 'openai';

interface AgentConfig {
  model: string;
  apiKey: string;
  baseURL?: string;
}

export class Agent {
  public maas: string;
  private config: AgentConfig;
  private client: OpenAI;

  constructor(maas: string) {
    this.maas = maas;

    // Set default configuration based on the MaaS provider
    switch (maas) {
      case 'qwen3coder':
        this.config = {
          model: 'qwen-max', // Updated to a valid Qwen model name
          apiKey:
            process.env.QWEN_API_KEY ||
            process.env.OPENAI_API_KEY ||
            'fake-key-for-demo',
          baseURL:
            process.env.QWEN_BASE_URL ||
            'https://dashscope.aliyuncs.com/compatible-mode/v1' // Qwen API endpoint
        };
        break;
      default:
        this.config = {
          model: 'gpt-4o-mini',
          apiKey: process.env.OPENAI_API_KEY || 'fake-key-for-demo',
          baseURL: process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1'
        };
    }

    // Initialize OpenAI client
    this.client = new OpenAI({
      apiKey: this.config.apiKey,
      baseURL: this.config.baseURL
    });
  }

  getConfig(): AgentConfig {
    return { ...this.config };
  }

  async chat(prompt: string): Promise<any> {
    const startTime = Date.now();
    const requestId = `req_${Math.random().toString(36).substr(2, 9)}`;

    try {
      console.log(`🤖 [AGENT] [${requestId}] LLM invocation started`);
      console.log(`📋 [AGENT] [${requestId}] MaaS: ${this.maas}`);
      console.log(`📦 [AGENT] [${requestId}] Model: ${this.config.model}`);
      console.log(
        `📏 [AGENT] [${requestId}] Prompt length: ${prompt.length} characters`
      );
      console.log(
        `📄 [AGENT] [${requestId}] Prompt preview: ${prompt.substring(0, 100)}${prompt.length > 100 ? '...' : ''}`
      );

      const response = await this.client.chat.completions.create({
        model: this.config.model,
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.7,
        max_tokens: 2048
      });

      const duration = Date.now() - startTime;
      const content = response.choices[0]?.message?.content || '';
      const promptTokens = response.usage?.prompt_tokens || 0;
      const completionTokens = response.usage?.completion_tokens || 0;
      const totalTokens = response.usage?.total_tokens || 0;

      console.log(
        `✅ [AGENT] [${requestId}] LLM invocation completed successfully`
      );
      console.log(`⏱️ [AGENT] [${requestId}] Response time: ${duration}ms`);
      console.log(
        `📊 [AGENT] [${requestId}] Tokens used - Prompt: ${promptTokens}, Completion: ${completionTokens}, Total: ${totalTokens}`
      );
      console.log(
        `📏 [AGENT] [${requestId}] Response length: ${content.length} characters`
      );
      console.log(
        `📄 [AGENT] [${requestId}] Response preview: ${content.substring(0, 100)}${content.length > 100 ? '...' : ''}`
      );

      return {
        response: content,
        model: response.model,
        usage: response.usage,
        duration: duration
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(
        `❌ [AGENT] [${requestId}] Error calling ${this.maas} after ${duration}ms:`,
        error
      );

      // Log error details
      if (error instanceof Error) {
        console.error(`📋 [AGENT] [${requestId}] Error name: ${error.name}`);
        console.error(
          `📋 [AGENT] [${requestId}] Error message: ${error.message}`
        );
        if (error.stack) {
          console.error(
            `📋 [AGENT] [${requestId}] Error stack: ${error.stack.substring(0, 500)}${error.stack.length > 500 ? '...' : ''}`
          );
        }
      }

      throw error;
    }
  }
}
