/**
 * Orizon Zero Trust Connect - Script Generator Microservice
 * For: Marco @ Syneto/Orizon
 *
 * Express server that generates agent installation scripts
 */

import express, { Request, Response, NextFunction } from 'express';
import dotenv from 'dotenv';
import winston from 'winston';
import {
  ScriptGenerator,
  GenerateScriptRequest,
  OsType,
} from './services/ScriptGenerator';

dotenv.config();

// Initialize logger
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      ),
    }),
  ],
});

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(express.json());

// Request logging middleware
app.use((req: Request, res: Response, next: NextFunction) => {
  logger.info(`${req.method} ${req.path}`);
  next();
});

// Initialize Script Generator
const scriptGenerator = new ScriptGenerator();

/**
 * Health check endpoint
 */
app.get('/health', (req: Request, res: Response) => {
  res.json({
    status: 'ok',
    service: 'script-generator',
    version: '2.0.1',
    timestamp: new Date().toISOString(),
  });
});

/**
 * Generate script for specific OS
 * POST /api/scripts/generate/:osType
 */
app.post('/api/scripts/generate/:osType', (req: Request, res: Response) => {
  try {
    const osType = req.params.osType as OsType;
    const data: GenerateScriptRequest = req.body;

    // Validate OS type
    if (!['linux', 'macos', 'windows'].includes(osType)) {
      return res.status(400).json({
        error: 'Invalid OS type',
        validTypes: ['linux', 'macos', 'windows'],
      });
    }

    // Validate required fields
    const requiredFields = [
      'nodeId',
      'nodeName',
      'agentToken',
      'hubHost',
      'hubSshPort',
      'tunnelType',
      'apiBaseUrl',
      'applicationPorts',
    ];

    for (const field of requiredFields) {
      if (!data[field as keyof GenerateScriptRequest]) {
        return res.status(400).json({
          error: `Missing required field: ${field}`,
        });
      }
    }

    // Generate script
    const script = scriptGenerator.generateScript(osType, data);

    logger.info(`📜 Script generated for ${osType}: node ${data.nodeId}`);

    // Return script
    res.setHeader('Content-Type', ScriptGenerator.getMimeType(osType));
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="orizon-install-${data.nodeName}${ScriptGenerator.getFileExtension(osType)}"`
    );
    res.send(script);
  } catch (error) {
    logger.error('Error generating script:', error);
    res.status(500).json({
      error: 'Failed to generate script',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

/**
 * Generate scripts for all platforms
 * POST /api/scripts/generate-all
 */
app.post('/api/scripts/generate-all', (req: Request, res: Response) => {
  try {
    const data: GenerateScriptRequest = req.body;

    // Validate required fields
    const requiredFields = [
      'nodeId',
      'nodeName',
      'agentToken',
      'hubHost',
      'hubSshPort',
      'tunnelType',
      'apiBaseUrl',
      'applicationPorts',
    ];

    for (const field of requiredFields) {
      if (!data[field as keyof GenerateScriptRequest]) {
        return res.status(400).json({
          error: `Missing required field: ${field}`,
        });
      }
    }

    // Generate all scripts
    const scripts = scriptGenerator.generateAllScripts(data);

    logger.info(`📜 All scripts generated for node ${data.nodeId}`);

    // Return scripts as JSON
    res.json({
      nodeId: data.nodeId,
      nodeName: data.nodeName,
      scripts: {
        linux: scripts.linux,
        macos: scripts.macos,
        windows: scripts.windows,
      },
      downloadUrls: {
        linux: `/api/scripts/download/${data.nodeId}/linux`,
        macos: `/api/scripts/download/${data.nodeId}/macos`,
        windows: `/api/scripts/download/${data.nodeId}/windows`,
      },
    });
  } catch (error) {
    logger.error('Error generating scripts:', error);
    res.status(500).json({
      error: 'Failed to generate scripts',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

/**
 * Error handling middleware
 */
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: err.message,
  });
});

/**
 * Start server
 */
app.listen(PORT, () => {
  logger.info(`╔════════════════════════════════════════════════════════════╗`);
  logger.info(`║  Orizon Script Generator Service v2.0.1                   ║`);
  logger.info(`║  Listening on http://localhost:${PORT}                       ║`);
  logger.info(`╚════════════════════════════════════════════════════════════╝`);
});

export default app;
