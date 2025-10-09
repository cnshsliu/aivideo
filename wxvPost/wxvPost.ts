import { chromium, Browser, Page, BrowserContext } from 'playwright';
import * as fs from "node:fs";

interface PlaywrightClientConfig {
  headless?: boolean;
}

class PlaywrightClient {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private storageFile: string = 'wxsession.json';

  constructor(config: PlaywrightClientConfig = {}) {
    // No initialization needed here
  }

  async connect(): Promise<void> {
    try {
      this.browser = await chromium.launch({ channel: 'chrome', headless: false });
      this.context = await this.browser.newContext({
        storageState: fs.existsSync(this.storageFile) ? JSON.parse(fs.readFileSync(this.storageFile, 'utf8')) : undefined,
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
      });
      this.page = await this.context.newPage();
      console.log("Successfully launched Playwright browser.");
    } catch (error) {
      console.error("Browser launch failed:", error);
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    if (this.page) {
      await this.page.close();
      console.log("Page closed.");
    }
    if (this.browser) {
      await this.browser.close();
      console.log("Browser closed.");
    }
  }

  async navigate(url: string): Promise<void> {
    if (!this.page) throw new Error("Page not initialized.");
    await this.page.goto(url);
  }

  async isSessionValid(cookieNames: string[]): Promise<boolean> {
    if (!this.page) throw new Error("Page not initialized.");
    const allCookies = await this.page.context().cookies();
    console.log(JSON.stringify(allCookies));
    const cookies: { [key: string]: string } = {};
    const now = Date.now() / 1000; // Convert to seconds
    for (const cookie of allCookies) {
      // Check if the cookie is in the list of required cookies and not expired
      if (cookieNames.includes(cookie.name) && cookie.expires > now) {
        cookies[cookie.name] = cookie.value;
      }
    }
    console.log("Valid Cookies");
    for (const [name, value] of Object.entries(cookies)) {
      console.log(`  ${name}: ${value}`);
    }

    const allFound = cookieNames.every(name => cookies.hasOwnProperty(name) && cookies[name] && cookies[name] !== '');
    return allFound;
  }

  async saveStorageState(): Promise<void> {
    if (!this.context) throw new Error("Context not initialized.");
    const storageState = await this.context.storageState();
    fs.writeFileSync(this.storageFile, JSON.stringify(storageState, null, 2));
    console.log("Storage state saved.");
  }

  async postVideo(videoPath: string, title: string, description: string): Promise<void> {
    if (!this.page) throw new Error("Page not initialized.");
    // Upload video file
    const fileInput = this.page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'demo.mp4',
      mimeType: 'video/mp4',
      buffer: fs.readFileSync(videoPath)
    });
    await this.saveStorageState();
    // Fill description in contenteditable div
    const descInput = this.page.locator('[contenteditable][data-placeholder="添加描述"]');
    await descInput.fill(title);
    // Fill short title in input field
    const titleInput = this.page.locator('input[placeholder*="概括视频主要内容"]');
    await titleInput.fill(description);
    // Check the original declaration checkbox
    const originalCheckbox = this.page.getByRole('checkbox', { name: '声明后，作品将展示原创标记，有机会获得广告收入。' });
    await originalCheckbox.check();
    // Check if protocol agreement dialog appears and check its checkbox
    const protoWrapper = this.page.locator('.original-proto-wrapper').filter({ hasText: '我已阅读并同意《原创声明须知》和《使用条款》。如滥用声明，平台将驳回并予以相关处置。' }).first();
    if (await protoWrapper.isVisible()) {
      const protoCheckbox = protoWrapper.locator('.ant-checkbox-input');
      await protoCheckbox.check();
    }
    // Click declare original button
    const declareOriginalButton = this.page.getByRole('button', { name: '声明原创' });
    await declareOriginalButton.click();
    await this.saveStorageState();

    // Click submit button
    let submitButton;
    while (true) {
      submitButton = this.page.getByRole('button', { name: '发表' });
      if (submitButton && !(await submitButton.evaluate(button => button.classList.contains('weui-desktop-btn_disabled')))) break;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    if (submitButton) await submitButton.click();
    await this.saveStorageState();
    console.log("Video post submitted");
  }
}


async function main() {
  const client = new PlaywrightClient();
  try {
    await client.connect();

    await client.navigate("https://channels.weixin.qq.com");
    // Check session
    let isSessionOkay = await client.isSessionValid(["sessionid", "wxuin"]);
    console.log("Initial session check:", isSessionOkay);

    if (!isSessionOkay) {
      await client.navigate("https://channels.weixin.qq.com/login.html");
      console.log("Navigated to login page. Waiting for session...");
      while (!(await client.isSessionValid(["sessionid", "wxuin"]))) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second before checking again
      }
      console.log("Session established.");
      await client.saveStorageState();
    }
    await client.navigate("https://channels.weixin.qq.com/platform/post/create");
    await new Promise(resolve => setTimeout(resolve, 5000));
    let isSessionOkay2 = await client.isSessionValid(["sessionid", "wxuin"]);
    await client.saveStorageState();
    await client.postVideo("/Users/lucas/dev/wxvPost/demo.mp4", "学习发表视频号", "#学习  #视频号");
    await client.saveStorageState();

  } catch (error) {
    console.error("Error:", error);
    // Keep browser open for manual inspection
    return;
  }
  //await client.disconnect();
}

main().catch((error) => {
  console.error("Unexpected error:", error);
  process.exit(1);
});
