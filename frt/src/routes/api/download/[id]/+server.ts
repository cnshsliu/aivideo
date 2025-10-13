import { error, json } from '@sveltejs/kit';
import { readFile, writeFile } from 'fs/promises';
import { join } from 'path';
import { db } from '$lib/server/db/index.js';
import { translationTask } from '$lib/server/db/schema.js';
import { eq } from 'drizzle-orm';

export async function GET({ params, url }) {
  try {
    const { id } = params;
    const format = url.searchParams.get('format') || 'markdown';

    console.log(
      '📥 [DOWNLOAD API] GET request for task ID:',
      id,
      'Format:',
      format
    );

    // Get task details from database
    const taskResult = await db
      .select()
      .from(translationTask)
      .where(eq(translationTask.taskId, id))
      .limit(1);

    if (taskResult.length === 0) {
      console.log('❌ [DOWNLOAD API] Task not found:', id);
      return error(404, { message: 'Task not found' });
    }

    const task = taskResult[0];

    if (task.status !== 'completed') {
      console.log(
        '❌ [DOWNLOAD API] Task not completed yet. Status:',
        task.status
      );
      return error(400, { message: 'Translation not completed yet' });
    }

    console.log(
      '✅ [DOWNLOAD API] Task found and completed, preparing download...'
    );

    let filePath: string;
    let contentType: string;
    let fileName: string;

    switch (format) {
      case 'markdown':
      case 'md':
        if (!task.markdownPath) {
          return error(404, { message: 'Markdown file not available' });
        }
        filePath = task.markdownPath;
        contentType = 'text/markdown';
        fileName = `translation_report_${id}.md`;
        break;

      case 'docx':
        // Check if we have a translated file using new naming convention
        const uploadsDir = join(process.cwd(), 'uploads');
        const translatedFileName = task.originalFileExtension
          ? `${id}_translated.${task.originalFileExtension}`
          : `${id}_translated.docx`;
        const translatedFilePath = join(uploadsDir, translatedFileName);

        // Try to read the translated file first
        try {
          await readFile(translatedFilePath);
          filePath = translatedFilePath;
          contentType =
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
          // Restore original filename with translated prefix
          fileName = task.originalFileName
            ? `translated_${task.originalFileName}`
            : `translated_document_${id}.docx`;
          console.log(
            '✅ [DOWNLOAD API] Using translated file:',
            translatedFilePath
          );
        } catch {
          // If translated file doesn't exist, fall back to original file
          if (task.sourceFilePath && task.sourceType === 'docx') {
            filePath = task.sourceFilePath;
            contentType =
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
            fileName = task.originalFileName || `original_${id}.docx`;
            console.log(
              '⚠️ [DOWNLOAD API] Using original file:',
              task.sourceFilePath
            );
          } else {
            // Generate a basic DOCX from task content
            filePath = await generateDocx(task);
            contentType =
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
            fileName = `generated_${id}.docx`;
            console.log('⚠️ [DOWNLOAD API] Generated DOCX file:', filePath);
          }
        }
        break;

      case 'pdf':
        if (!task.pdfPath) {
          // Generate PDF from markdown if not exists
          filePath = await generatePdf(task);
          contentType = 'application/pdf';
          fileName = `translation_report_${id}.pdf`;
        } else {
          filePath = task.pdfPath;
          contentType = 'application/pdf';
          fileName = `translation_report_${id}.pdf`;
        }
        break;

      default:
        return error(400, { message: 'Unsupported format' });
    }

    // Read the file
    console.log('📄 [DOWNLOAD API] Attempting to read file:', filePath);
    const fileContent = await readFile(filePath);
    console.log(
      '✅ [DOWNLOAD API] File read successfully, size:',
      fileContent.length,
      'bytes'
    );

    // Return file with appropriate headers
    return new Response(fileContent, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `attachment; filename=\"${fileName}\"`,
        'Cache-Control': 'no-cache, no-store, must-revalidate'
      }
    });
  } catch (err) {
    console.error('❌ [DOWNLOAD API] File download error:', err);
    return error(500, { message: 'Internal server error' });
  }
}

async function generateDocx(taskData: any): Promise<string> {
  try {
    // Use the docx library to generate a proper DOCX file
    const { Document, Paragraph, TextRun, HeadingLevel, Packer } = await import(
      'docx'
    );

    // Parse the content to extract sections
    const content = taskData.sourceContent || '';
    const lines = content.split('\n');

    // Create document elements
    const children = [];

    for (const line of lines) {
      if (line.startsWith('# ')) {
        // Main heading
        children.push(
          new Paragraph({
            text: line.substring(2),
            heading: HeadingLevel.HEADING_1
          })
        );
      } else if (line.startsWith('## ')) {
        // Subheading
        children.push(
          new Paragraph({
            text: line.substring(3),
            heading: HeadingLevel.HEADING_2
          })
        );
      } else if (line.startsWith('**') && line.endsWith('**')) {
        // Bold text (likely a key-value pair)
        children.push(
          new Paragraph({
            children: [
              new TextRun({
                text: line,
                bold: true
              })
            ]
          })
        );
      } else if (line.startsWith('- ')) {
        // List item
        children.push(
          new Paragraph({
            text: line.substring(2),
            bullet: {
              level: 0
            }
          })
        );
      } else if (line.trim() === '') {
        // Empty line - add spacing
        children.push(new Paragraph(''));
      } else {
        // Regular paragraph
        children.push(new Paragraph(line));
      }
    }

    // Create the document
    const doc = new Document({
      sections: [
        {
          properties: {},
          children: children
        }
      ]
    });

    // Generate the file path
    const uploadDir = join(process.cwd(), 'uploads');
    const filePath = join(uploadDir, `${taskData.taskId}_generated.docx`);

    // Pack and save the document
    const buffer = await Packer.toBuffer(doc);
    await writeFile(filePath, buffer);

    return filePath;
  } catch (error) {
    console.error('❌ [DOWNLOAD API] Failed to generate DOCX:', error);
    // Fallback: create a simple text file
    const uploadDir = join(process.cwd(), 'uploads');
    const filePath = join(uploadDir, `${taskData.taskId}_fallback.txt`);
    const fallbackContent = `Translation Report

Source Language: ${taskData.sourceLanguage}
Target Language: ${taskData.targetLanguage}
Task ID: ${taskData.taskId}

Content:
${content}`;

    await writeFile(filePath, fallbackContent);
    return filePath;
  }
}

async function generatePdf(taskData: any): Promise<string> {
  // In production, you'd use a library like puppeteer or pandoc
  // For now, create a simple markdown file as PDF placeholder
  const uploadDir = join(process.cwd(), 'uploads');
  const filePath = join(uploadDir, `${taskData.taskId}_report.md`);
  const content = `# Translation Report

**Source Language:** ${taskData.sourceLanguage}
**Target Language:** ${taskData.targetLanguage}
**Task ID:** ${taskData.taskId}
**Status:** ${taskData.status}

---

## Translated Content

${taskData.sourceContent || 'No content available'}

---

*Generated on ${new Date().toISOString()}*`;

  await writeFile(filePath, content);
  return filePath;
}
