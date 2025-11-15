#!/usr/bin/env node

import { Command } from 'commander';
import dotenv from 'dotenv';
import { createGuacamoleClient } from './guac';
import { createDefaultSecretStore, SecretRef } from './secrets';
import { createOrizonSSO } from './integration/orizon-sso';
import { NodeSync } from './integration/node-sync';
import { Connection } from './models';
import winston from 'winston';

// Load environment variables
dotenv.config();

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.colorize(),
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
      const metaStr = Object.keys(meta).length ? JSON.stringify(meta, null, 2) : '';
      return `${timestamp} [${level}]: ${message} ${metaStr}`;
    })
  ),
  transports: [new winston.transports.Console()],
});

const program = new Command();

program
  .name('guacctl')
  .description('Orizon Zero Trust Connect - Guacamole Integration CLI')
  .version('1.0.0');

// Global options
program
  .option('--url <url>', 'Guacamole URL', process.env.GUAC_URL)
  .option('--datasource <ds>', 'Guacamole datasource', process.env.GUAC_DATASOURCE || 'mysql')
  .option('--insecure', 'Disable TLS verification (use with caution!)', false)
  .option('--verbose', 'Enable verbose logging', false);

/**
 * Login command
 */
program
  .command('login')
  .description('Authenticate with Guacamole')
  .option('-u, --user <username>', 'Guacamole username', process.env.GUAC_ADMIN_USER)
  .option('-p, --password <password>', 'Guacamole password', process.env.GUAC_ADMIN_PASS)
  .action(async (options) => {
    try {
      const globalOpts = program.opts();
      if (globalOpts.verbose) logger.level = 'debug';

      if (!options.user || !options.password) {
        logger.error('Username and password are required');
        process.exit(1);
      }

      const client = createGuacamoleClient({
        url: globalOpts.url,
        datasource: globalOpts.datasource,
        verifyTLS: !globalOpts.insecure,
      });

      const token = await client.getToken(options.user, options.password);
      logger.info('✓ Successfully authenticated with Guacamole', {
        username: token.username,
        datasource: token.dataSource,
      });

      console.log(`\nAuth Token: ${token.authToken}`);
      console.log('\nTo use this token, set it in your environment:');
      console.log(`export GUAC_TOKEN="${token.authToken}"`);
    } catch (error: any) {
      logger.error('Login failed', { error: error.message });
      process.exit(1);
    }
  });

/**
 * SSO Login command
 */
program
  .command('sso-login')
  .description('Authenticate with Orizon SSO and get Guacamole access')
  .option('-e, --email <email>', 'Orizon email', process.env.ORIZON_ADMIN_EMAIL)
  .option('-p, --password <password>', 'Orizon password', process.env.ORIZON_ADMIN_PASS)
  .action(async (options) => {
    try {
      const globalOpts = program.opts();
      if (globalOpts.verbose) logger.level = 'debug';

      if (!options.email || !options.password) {
        logger.error('Email and password are required');
        process.exit(1);
      }

      // Step 1: Authenticate with Orizon
      const orizonSSO = createOrizonSSO({ verifyTLS: !globalOpts.insecure, logger });
      const orizonToken = await orizonSSO.login(options.email, options.password);
      logger.info('✓ Authenticated with Orizon', {
        email: options.email,
        role: orizonToken.user?.role,
      });

      // Step 2: Get Guacamole credentials
      const guacCreds = await orizonSSO.getGuacamoleCredentials();

      // Step 3: Authenticate with Guacamole
      const guacClient = createGuacamoleClient({
        url: globalOpts.url,
        datasource: globalOpts.datasource,
        verifyTLS: !globalOpts.insecure,
      });

      const guacToken = await guacClient.getToken(guacCreds.username, guacCreds.password);
      logger.info('✓ Authenticated with Guacamole via SSO');

      console.log(`\nOrizon Token: ${orizonToken.access_token}`);
      console.log(`Guacamole Token: ${guacToken.authToken}`);
      console.log('\n✓ SSO login successful! You now have access to both Orizon and Guacamole.');
    } catch (error: any) {
      logger.error('SSO login failed', { error: error.message });
      process.exit(1);
    }
  });

/**
 * Create SSH connection
 */
program
  .command('create-ssh')
  .description('Create an SSH connection in Guacamole')
  .requiredOption('--name <name>', 'Connection name')
  .requiredOption('--host <hostname>', 'SSH hostname or IP')
  .option('--port <port>', 'SSH port', '22')
  .requiredOption('--user <username>', 'SSH username')
  .option('--password <password>', 'SSH password')
  .option('--password-ref <ref>', 'Secret reference for password')
  .option('--ssh-key <key>', 'SSH private key')
  .option('--ssh-key-ref <ref>', 'Secret reference for SSH private key')
  .option('--no-sftp', 'Disable SFTP')
  .action(async (options) => {
    try {
      const globalOpts = program.opts();
      if (globalOpts.verbose) logger.level = 'debug';

      const secretStore = createDefaultSecretStore();
      const client = createGuacamoleClient({
        url: globalOpts.url,
        datasource: globalOpts.datasource,
        verifyTLS: !globalOpts.insecure,
        secretStore,
      });

      // Authenticate
      await client.getToken(
        process.env.GUAC_ADMIN_USER!,
        process.env.GUAC_ADMIN_PASS!
      );

      // Resolve password/key from secret store if needed
      let password = options.password;
      let privateKey = options.sshKey;

      if (options.passwordRef) {
        password = await secretStore.getSecret(options.passwordRef);
      }

      if (options.sshKeyRef) {
        privateKey = await secretStore.getSecret(options.sshKeyRef);
      }

      // Create connection
      const connection = await client.createSSHConnection({
        name: options.name,
        hostname: options.host,
        port: options.port,
        username: options.user,
        password,
        privateKey,
        enableSFTP: options.sftp,
      });

      logger.info('✓ SSH connection created', {
        id: connection.identifier,
        name: connection.name,
      });

      console.log(`\nConnection ID: ${connection.identifier}`);
      console.log(`Access URL: ${globalOpts.url}/#/client/${connection.identifier}`);
    } catch (error: any) {
      logger.error('Failed to create SSH connection', { error: error.message });
      process.exit(1);
    }
  });

/**
 * Create RDP connection
 */
program
  .command('create-rdp')
  .description('Create an RDP connection in Guacamole')
  .requiredOption('--name <name>', 'Connection name')
  .requiredOption('--host <hostname>', 'RDP hostname or IP')
  .option('--port <port>', 'RDP port', '3389')
  .requiredOption('--user <username>', 'RDP username')
  .option('--password <password>', 'RDP password')
  .option('--password-ref <ref>', 'Secret reference for password')
  .option('--domain <domain>', 'Windows domain')
  .option('--security <mode>', 'Security mode (any|nla|tls|rdp)', 'any')
  .option('--enable-drive', 'Enable drive redirection (disabled by default)')
  .option('--enable-clipboard', 'Enable clipboard (disabled by default)')
  .action(async (options) => {
    try {
      const globalOpts = program.opts();
      if (globalOpts.verbose) logger.level = 'debug';

      const secretStore = createDefaultSecretStore();
      const client = createGuacamoleClient({
        url: globalOpts.url,
        datasource: globalOpts.datasource,
        verifyTLS: !globalOpts.insecure,
        secretStore,
      });

      // Authenticate
      await client.getToken(
        process.env.GUAC_ADMIN_USER!,
        process.env.GUAC_ADMIN_PASS!
      );

      // Resolve password from secret store if needed
      let password = options.password;
      if (options.passwordRef) {
        password = await secretStore.getSecret(options.passwordRef);
      }

      if (!password) {
        logger.error('Password is required (--password or --password-ref)');
        process.exit(1);
      }

      // Create connection
      const connection = await client.createRDPConnection({
        name: options.name,
        hostname: options.host,
        port: options.port,
        username: options.user,
        password,
        domain: options.domain,
        security: options.security,
        enableDrive: options.enableDrive || false,
        enableClipboard: options.enableClipboard || false,
      });

      logger.info('✓ RDP connection created', {
        id: connection.identifier,
        name: connection.name,
      });

      console.log(`\nConnection ID: ${connection.identifier}`);
      console.log(`Access URL: ${globalOpts.url}/#/client/${connection.identifier}`);
    } catch (error: any) {
      logger.error('Failed to create RDP connection', { error: error.message });
      process.exit(1);
    }
  });

/**
 * List connections
 */
program
  .command('list')
  .description('List all Guacamole connections')
  .action(async () => {
    try {
      const globalOpts = program.opts();
      if (globalOpts.verbose) logger.level = 'debug';

      const client = createGuacamoleClient({
        url: globalOpts.url,
        datasource: globalOpts.datasource,
        verifyTLS: !globalOpts.insecure,
      });

      await client.getToken(
        process.env.GUAC_ADMIN_USER!,
        process.env.GUAC_ADMIN_PASS!
      );

      const connections = await client.getConnections();

      console.log('\nGuacamole Connections:\n');
      for (const [id, conn] of Object.entries(connections)) {
        const connection = conn as Connection;
        console.log(`[${id}] ${connection.name} (${connection.protocol})`);
        if (connection.parameters?.hostname && connection.parameters?.port) {
          console.log(`    Host: ${connection.parameters.hostname}:${connection.parameters.port}`);
        }
        console.log(`    Active: ${connection.activeConnections || 0}`);
        console.log('');
      }
    } catch (error: any) {
      logger.error('Failed to list connections', { error: error.message });
      process.exit(1);
    }
  });

/**
 * Grant permission
 */
program
  .command('grant')
  .description('Grant user permission to a connection')
  .requiredOption('--user <username>', 'Guacamole username')
  .requiredOption('--connection <id>', 'Connection ID')
  .option('--perm <permission>', 'Permission (READ|UPDATE|DELETE|ADMINISTER)', 'READ')
  .action(async (options) => {
    try {
      const globalOpts = program.opts();
      if (globalOpts.verbose) logger.level = 'debug';

      const client = createGuacamoleClient({
        url: globalOpts.url,
        datasource: globalOpts.datasource,
        verifyTLS: !globalOpts.insecure,
      });

      await client.getToken(
        process.env.GUAC_ADMIN_USER!,
        process.env.GUAC_ADMIN_PASS!
      );

      await client.grantConnectionAccess(options.user, options.connection, [options.perm]);

      logger.info('✓ Permission granted', {
        user: options.user,
        connection: options.connection,
        permission: options.perm,
      });
    } catch (error: any) {
      logger.error('Failed to grant permission', { error: error.message });
      process.exit(1);
    }
  });

/**
 * Sync Orizon nodes to Guacamole
 */
program
  .command('sync-nodes')
  .description('Sync Orizon nodes to Guacamole connections')
  .option('--ssh', 'Create SSH connections', true)
  .option('--rdp', 'Create RDP connections', false)
  .option('--dry-run', 'Show what would be done without making changes', false)
  .action(async (options) => {
    try {
      const globalOpts = program.opts();
      if (globalOpts.verbose) logger.level = 'debug';

      // Authenticate with Orizon
      const orizonSSO = createOrizonSSO({ verifyTLS: !globalOpts.insecure, logger });
      const orizonToken = await orizonSSO.login(
        process.env.ORIZON_ADMIN_EMAIL!,
        process.env.ORIZON_ADMIN_PASS!
      );

      // Authenticate with Guacamole
      const guacClient = createGuacamoleClient({
        url: globalOpts.url,
        datasource: globalOpts.datasource,
        verifyTLS: !globalOpts.insecure,
      });

      const guacCreds = await orizonSSO.getGuacamoleCredentials();
      await guacClient.getToken(guacCreds.username, guacCreds.password);

      // Sync nodes
      const nodeSync = new NodeSync({
        orizonApiUrl: process.env.ORIZON_API_URL!,
        orizonToken: orizonToken.access_token,
        verifyTLS: !globalOpts.insecure,
        logger,
      });

      const results = await nodeSync.syncAllNodes(guacClient, {
        createSSH: options.ssh,
        createRDP: options.rdp,
        dryRun: options.dryRun,
      });

      logger.info(`✓ Synced ${results.size} nodes to Guacamole`);

      if (!options.dryRun) {
        console.log('\nSync Results:\n');
        for (const [nodeId, conns] of results.entries()) {
          console.log(`Node ${nodeId}:`);
          if (conns.ssh) {
            console.log(`  SSH: ${conns.ssh.identifier}`);
          }
          if (conns.rdp) {
            console.log(`  RDP: ${conns.rdp.identifier}`);
          }
        }
      }
    } catch (error: any) {
      logger.error('Node sync failed', { error: error.message });
      process.exit(1);
    }
  });

/**
 * Test Edge Ubuntu connection
 */
program
  .command('test-edge-ubuntu')
  .description('Test connection to Edge Ubuntu node')
  .option('--ssh', 'Test SSH connection', true)
  .option('--rdp', 'Test RDP connection', false)
  .action(async (options) => {
    try {
      const globalOpts = program.opts();
      if (globalOpts.verbose) logger.level = 'debug';

      const client = createGuacamoleClient({
        url: globalOpts.url,
        datasource: globalOpts.datasource,
        verifyTLS: !globalOpts.insecure,
      });

      await client.getToken(
        process.env.GUAC_ADMIN_USER!,
        process.env.GUAC_ADMIN_PASS!
      );

      if (options.ssh) {
        logger.info('Creating SSH connection to Edge Ubuntu...');
        const sshConn = await client.createSSHConnection({
          name: 'Edge Ubuntu - SSH',
          hostname: process.env.TEST_EDGE_UBUNTU_IP || '10.211.55.20',
          port: '22',
          username: process.env.SECRET__SSH__EDGE_UBUNTU_USER || 'parallels',
          password: process.env.SECRET__SSH__EDGE_UBUNTU_PASS || 'profano.69',
          enableSFTP: true,
        });

        logger.info('✓ SSH connection created', { id: sshConn.identifier });
        console.log(`\nSSH Access URL: ${globalOpts.url}/#/client/${sshConn.identifier}`);
      }

      if (options.rdp) {
        logger.info('Creating RDP connection to Edge Ubuntu...');
        const rdpConn = await client.createRDPConnection({
          name: 'Edge Ubuntu - RDP',
          hostname: process.env.TEST_EDGE_UBUNTU_IP || '10.211.55.20',
          port: '3389',
          username: process.env.SECRET__RDP__EDGE_UBUNTU_USER || 'parallels',
          password: process.env.SECRET__RDP__EDGE_UBUNTU_PASS || 'profano.69',
          security: 'any',
          enableDrive: false,
          enableClipboard: false,
        });

        logger.info('✓ RDP connection created', { id: rdpConn.identifier });
        console.log(`\nRDP Access URL: ${globalOpts.url}/#/client/${rdpConn.identifier}`);
      }
    } catch (error: any) {
      logger.error('Test failed', { error: error.message });
      process.exit(1);
    }
  });

program.parse();
