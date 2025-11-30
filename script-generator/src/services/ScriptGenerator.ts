/**
 * Orizon Zero Trust Connect - Script Generator Service
 * For: Marco @ Syneto/Orizon
 *
 * Generates installation scripts from Handlebars templates
 */

import Handlebars from 'handlebars';
import fs from 'fs';
import path from 'path';

export interface ApplicationPort {
  local: number;
  remote: number;
}

export interface GenerateScriptRequest {
  nodeId: string;
  nodeName: string;
  agentToken: string;
  hubHost: string;
  hubSshPort: number;
  tunnelType: 'SSH' | 'SSL';
  apiBaseUrl: string;
  applicationPorts: Record<string, ApplicationPort>;
  // Optional: if not provided, will be calculated from nodeId
  systemTunnelPort?: number;
  terminalTunnelPort?: number;
}

export type OsType = 'linux' | 'macos' | 'windows';

export class ScriptGenerator {
  private templates: Map<OsType, HandlebarsTemplateDelegate>;

  constructor() {
    this.templates = new Map();
    this.loadTemplates();
  }

  /**
   * Load all Handlebars templates
   */
  private loadTemplates(): void {
    const templatesDir = path.join(__dirname, '..', 'templates');

    const templateFiles: Record<OsType, string> = {
      linux: 'install_linux.sh.hbs',
      macos: 'install_macos.sh.hbs',
      windows: 'install_windows.ps1.hbs',
    };

    for (const [osType, filename] of Object.entries(templateFiles)) {
      const templatePath = path.join(templatesDir, filename);
      const templateSource = fs.readFileSync(templatePath, 'utf-8');
      const template = Handlebars.compile(templateSource);
      this.templates.set(osType as OsType, template);
    }
  }

  /**
   * Calculate deterministic tunnel ports from node ID
   * Uses MD5 hash of node ID to generate consistent port numbers
   */
  private calculateTunnelPorts(nodeId: string): { systemPort: number; terminalPort: number } {
    // Simple hash function for browser/node compatibility
    let hash = 0;
    for (let i = 0; i < nodeId.length; i++) {
      const char = nodeId.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    hash = Math.abs(hash);

    // System tunnel: port range 9000-9999
    const systemPort = 9000 + (hash % 1000);

    // Terminal tunnel: port range 10000-59999
    const terminalPort = 10000 + (hash % 50000);

    return { systemPort, terminalPort };
  }

  /**
   * Generate installation script for specified OS
   */
  public generateScript(osType: OsType, data: GenerateScriptRequest): string {
    const template = this.templates.get(osType);
    if (!template) {
      throw new Error(`Template not found for OS type: ${osType}`);
    }

    // Calculate tunnel ports if not provided
    const tunnelPorts = this.calculateTunnelPorts(data.nodeId);

    // Prepare template data
    const templateData = {
      ...data,
      timestamp: new Date().toISOString(),
      systemTunnelPort: data.systemTunnelPort || tunnelPorts.systemPort,
      terminalTunnelPort: data.terminalTunnelPort || tunnelPorts.terminalPort,
    };

    // Generate script
    const script = template(templateData);

    return script;
  }

  /**
   * Generate scripts for all platforms
   */
  public generateAllScripts(data: GenerateScriptRequest): Record<OsType, string> {
    const scripts: Record<OsType, string> = {
      linux: this.generateScript('linux', data),
      macos: this.generateScript('macos', data),
      windows: this.generateScript('windows', data),
    };

    return scripts;
  }

  /**
   * Get file extension for OS type
   */
  public static getFileExtension(osType: OsType): string {
    switch (osType) {
      case 'linux':
      case 'macos':
        return '.sh';
      case 'windows':
        return '.ps1';
      default:
        return '';
    }
  }

  /**
   * Get MIME type for OS type
   */
  public static getMimeType(osType: OsType): string {
    switch (osType) {
      case 'linux':
      case 'macos':
        return 'application/x-sh';
      case 'windows':
        return 'application/x-powershell';
      default:
        return 'text/plain';
    }
  }
}
