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

export interface HubServer {
  name: string;        // e.g., "Hub1", "Hub2"
  host: string;        // e.g., "139.59.149.48"
  sshPort: number;     // e.g., 2222
  isPrimary: boolean;  // Primary hub for API calls
}

export interface GenerateScriptRequest {
  nodeId: string;
  nodeName: string;
  agentToken: string;
  // Legacy single hub support (deprecated)
  hubHost?: string;
  hubSshPort?: number;
  // New: Multi-hub support
  hubServers?: HubServer[];
  tunnelType: 'SSH' | 'SSL';
  apiBaseUrl: string;
  applicationPorts: Record<string, ApplicationPort>;
  // Optional: if not provided, will be calculated from nodeId
  systemTunnelPort?: number;
  terminalTunnelPort?: number;
  httpsTunnelPort?: number;
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

    // Build hub servers array (multi-hub support with backward compatibility)
    let hubServers: HubServer[] = data.hubServers || [];
    if (hubServers.length === 0 && data.hubHost) {
      // Legacy single hub mode
      hubServers = [{
        name: 'Hub1',
        host: data.hubHost,
        sshPort: data.hubSshPort || 2222,
        isPrimary: true,
      }];
    }

    // Get port mappings from applicationPorts or use defaults
    const terminalPorts = data.applicationPorts?.TERMINAL || { local: 22, remote: tunnelPorts.terminalPort };
    const httpsPorts = data.applicationPorts?.HTTPS || { local: 443, remote: tunnelPorts.terminalPort + 1 };

    // Prepare template data
    const templateData = {
      ...data,
      timestamp: new Date().toISOString(),
      systemTunnelPort: data.systemTunnelPort || tunnelPorts.systemPort,
      terminalTunnelPort: terminalPorts.remote,
      httpsTunnelPort: httpsPorts.remote,
      localSshPort: terminalPorts.local,
      localHttpsPort: httpsPorts.local,
      // Multi-hub support
      hubServers,
      hasMultipleHubs: hubServers.length > 1,
      primaryHub: hubServers.find(h => h.isPrimary) || hubServers[0],
      // Backward compatibility
      hubHost: data.hubHost || (hubServers[0]?.host || ''),
      hubSshPort: data.hubSshPort || (hubServers[0]?.sshPort || 2222),
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
