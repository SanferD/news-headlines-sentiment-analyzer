import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs';
import * as AdmZip from 'adm-zip'
import * as crypto from "crypto"
import { execSync } from 'child_process';
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import { Construct } from 'constructs';

export function downloadFileSync(url: string, filePath: string): void {
  const command = `curl -o ${filePath} ${url}`;
  execSync(command);
}

export function computeSHA256Sync(filePath: string): string {
  const fileData = fs.readFileSync(filePath);
  const hash = crypto.createHash('sha256').update(fileData);
  const hashDigest = hash.digest('hex');
  return hashDigest;
}


export function createTempDirectory(): string {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'temp-'));
  return tempDir;
}

export function extractZip(zipFilePath: string): string {
  const zip = new AdmZip(zipFilePath);
  const extractedPath = path.join(os.tmpdir(), path.basename(zipFilePath, '.zip'));

  zip.extractAllTo(extractedPath, true);
  return extractedPath;
}

export function getDefaultVpc(app: Construct): ec2.IVpc {
  return ec2.Vpc.fromLookup(app, "DefaultVpc", {isDefault: true})
}
