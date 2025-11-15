import { GuacamoleClient } from '../guac';
import { Connection } from '../models/connections';
import winston from 'winston';
import axios, { AxiosInstance } from 'axios';

/**
 * Node synchronization between Orizon and Guacamole
 * Automatically creates Guacamole connections for Orizon nodes
 */

export interface OrizonNode {
  id: string;
  name: string;
  ip_address: string;
  ssh_port?: number;
  rdp_port?: number;
  ssh_username?: string;
  ssh_password?: string;
  rdp_username?: string;
  rdp_password?: string;
  node_type?: string;
  status?: string;
  capabilities?: string[];
}

export interface NodeSyncConfig {
  orizonApiUrl: string;
  orizonToken: string;
  verifyTLS?: boolean;
  logger?: winston.Logger;
}

export class NodeSync {
  private api: AxiosInstance;
  private logger: winston.Logger;

  constructor(config: NodeSyncConfig) {
    this.logger =
      config.logger ||
      winston.createLogger({
        level: process.env.LOG_LEVEL || 'info',
        format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
        transports: [new winston.transports.Console()],
      });

    this.api = axios.create({
      baseURL: config.orizonApiUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${config.orizonToken}`,
      },
      httpsAgent: config.verifyTLS === false ? { rejectUnauthorized: false } : undefined,
    });
  }

  /**
   * Get all nodes from Orizon
   */
  async getOrizonNodes(): Promise<OrizonNode[]> {
    try {
      const response = await this.api.get<OrizonNode[]>('/nodes');
      this.logger.info(`Retrieved ${response.data.length} nodes from Orizon`);
      return response.data;
    } catch (error: any) {
      this.logger.error('Failed to get Orizon nodes', {
        error: error.message,
        status: error.response?.status,
      });
      throw new Error(`Failed to get Orizon nodes: ${error.message}`);
    }
  }

  /**
   * Sync a single node to Guacamole
   * Creates SSH and/or RDP connections based on node capabilities
   */
  async syncNodeToGuacamole(
    node: OrizonNode,
    guacClient: GuacamoleClient,
    options: {
      createSSH?: boolean;
      createRDP?: boolean;
      sshUsername?: string;
      sshPassword?: string;
      rdpUsername?: string;
      rdpPassword?: string;
    } = {}
  ): Promise<{
    ssh?: Connection;
    rdp?: Connection;
  }> {
    const result: { ssh?: Connection; rdp?: Connection } = {};

    // Create SSH connection
    if (options.createSSH !== false) {
      try {
        const sshConnection = await guacClient.createSSHConnection({
          name: `${node.name} - SSH`,
          hostname: node.ip_address,
          port: String(node.ssh_port || 22),
          username: options.sshUsername || node.ssh_username || 'parallels',
          password: options.sshPassword || node.ssh_password || 'profano.69',
          enableSFTP: true,
        });

        result.ssh = sshConnection;
        this.logger.info(`Created SSH connection for node ${node.name}`, {
          connectionId: sshConnection.identifier,
        });
      } catch (error: any) {
        this.logger.error(`Failed to create SSH connection for node ${node.name}`, {
          error: error.message,
        });
      }
    }

    // Create RDP connection if node has RDP capability
    if (options.createRDP && (node.capabilities?.includes('rdp') || node.rdp_port)) {
      try {
        const rdpConnection = await guacClient.createRDPConnection({
          name: `${node.name} - RDP`,
          hostname: node.ip_address,
          port: String(node.rdp_port || 3389),
          username: options.rdpUsername || node.rdp_username || 'parallels',
          password: options.rdpPassword || node.rdp_password || 'profano.69',
          security: 'any',
          enableDrive: false,
          enableClipboard: false,
        });

        result.rdp = rdpConnection;
        this.logger.info(`Created RDP connection for node ${node.name}`, {
          connectionId: rdpConnection.identifier,
        });
      } catch (error: any) {
        this.logger.error(`Failed to create RDP connection for node ${node.name}`, {
          error: error.message,
        });
      }
    }

    return result;
  }

  /**
   * Sync all Orizon nodes to Guacamole
   */
  async syncAllNodes(
    guacClient: GuacamoleClient,
    options: {
      createSSH?: boolean;
      createRDP?: boolean;
      dryRun?: boolean;
    } = {}
  ): Promise<Map<string, { ssh?: Connection; rdp?: Connection }>> {
    const nodes = await this.getOrizonNodes();
    const results = new Map<string, { ssh?: Connection; rdp?: Connection }>();

    this.logger.info(`Syncing ${nodes.length} nodes to Guacamole`, {
      dryRun: options.dryRun || false,
    });

    for (const node of nodes) {
      if (options.dryRun) {
        this.logger.info(`[DRY RUN] Would sync node: ${node.name} (${node.ip_address})`);
        continue;
      }

      try {
        const result = await this.syncNodeToGuacamole(node, guacClient, {
          createSSH: options.createSSH,
          createRDP: options.createRDP,
        });
        results.set(node.id, result);
      } catch (error: any) {
        this.logger.error(`Failed to sync node ${node.name}`, { error: error.message });
      }
    }

    return results;
  }

  /**
   * Get connection URL for a node in Guacamole
   */
  getConnectionUrl(connectionId: string, guacamoleUrl: string): string {
    return `${guacamoleUrl}/#/client/${connectionId}`;
  }

  /**
   * Create connection mapping in Orizon database
   * This stores the Guacamole connection ID with the Orizon node
   */
  async updateNodeGuacamoleConnection(
    nodeId: string,
    sshConnectionId?: string,
    rdpConnectionId?: string
  ): Promise<void> {
    try {
      await this.api.patch(`/nodes/${nodeId}`, {
        guacamole_ssh_connection_id: sshConnectionId,
        guacamole_rdp_connection_id: rdpConnectionId,
      });

      this.logger.info(`Updated node ${nodeId} with Guacamole connection IDs`);
    } catch (error: any) {
      this.logger.warn(`Failed to update node with Guacamole connection IDs`, {
        nodeId,
        error: error.message,
      });
    }
  }
}
