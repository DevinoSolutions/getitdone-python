/**
 * Regenerate tests/fixtures/webhook_vectors.json from the PRODUCER's own code.
 *
 * The vectors are what proves the Python verifier is byte-compatible with the
 * service that signs real deliveries. They are therefore NOT produced by a
 * Python re-implementation, and not by a JS re-implementation either: this
 * script imports `signWebhookPayload` from the actual
 * `packages/api-contracts/src/webhooks/signing.ts` in the GetItDone monorepo
 * and runs it.
 *
 * Usage (Node >= 22.18, which strips TypeScript types natively):
 *
 *   GETITDONE_MONOREPO=/path/to/GetItDone \
 *     node scripts/generate-webhook-vectors.mjs > tests/fixtures/webhook_vectors.json
 *
 * The monorepo is READ-ONLY: the two source files are copied to a temp dir and
 * only their extensionless relative import is rewritten there (Node's ESM
 * resolver needs the explicit `.ts`). The signing algorithm is untouched.
 */
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

const monorepo = process.env.GETITDONE_MONOREPO
if (!monorepo) {
    console.error('GETITDONE_MONOREPO must point at a checkout of the GetItDone app monorepo.')
    process.exit(1)
}

const sourceDir = join(monorepo, 'packages', 'api-contracts', 'src', 'webhooks')
const workDir = mkdtempSync(join(tmpdir(), 'gid-webhook-vectors-'))

writeFileSync(join(workDir, 'ids.ts'), readFileSync(join(sourceDir, 'ids.ts')))
writeFileSync(
    join(workDir, 'signing.ts'),
    readFileSync(join(sourceDir, 'signing.ts'), 'utf8').replace(
        "from './ids'",
        "from './ids.ts'",
    ),
)

const { signWebhookPayload } = await import(pathToFileURL(join(workDir, 'signing.ts')).href)

/**
 * Real secrets are `whsec_` + randomBase64Url(32), so their material routinely
 * contains `-` and `_`. The fixed key bytes below are chosen to GUARANTEE both
 * characters appear: that is what makes these vectors prove the base64url key
 * derivation rather than plain base64, which would decode different bytes (or
 * refuse to decode at all).
 */
const keyBytes = (tag) =>
    Buffer.from([0xfb, 0xff, 0xbe, 0xfb, 0xef, 0xbe, tag, ...Buffer.from('gid-vector-key-pad-')])
const b64url = (buffer) => buffer.toString('base64url')
const SECRET_A = 'whsec_' + b64url(keyBytes(0x41))
const SECRET_B = 'whsec_' + b64url(keyBytes(0x42))
const SECRET_NO_PREFIX = b64url(keyBytes(0x43))

for (const secret of [SECRET_A, SECRET_B, SECRET_NO_PREFIX]) {
    const material = secret.startsWith('whsec_') ? secret.slice(6) : secret
    if (!material.includes('-') || !material.includes('_')) {
        console.error(`vector secret ${material} does not exercise base64url characters`)
        process.exit(1)
    }
}

const cases = [
    {
        name: 'task_created_single_secret',
        description: 'A normal task.created delivery signed with one active secret.',
        id: 'evt_01J8Z0Q5X8N1V2W3T4Y5Z6A7B8',
        timestamp_seconds: 1785000000,
        raw_body: JSON.stringify({
            id: 'evt_01J8Z0Q5X8N1V2W3T4Y5Z6A7B8',
            type: 'task.created',
            created_at: '2026-08-05T12:00:00.000Z',
            data: { id: 'T-123', title: 'Ship the Python SDK', status: 'TODO' },
        }),
        secrets: [SECRET_A],
    },
    {
        name: 'task_updated_rotation_two_secrets',
        description:
            'Mid-rotation delivery: current AND previous secret each sign, so the header carries two v1 entries.',
        id: 'evt_01J8Z0Q5X8N1V2W3T4Y5Z6A7C9',
        timestamp_seconds: 1785000060,
        raw_body: JSON.stringify({
            id: 'evt_01J8Z0Q5X8N1V2W3T4Y5Z6A7C9',
            type: 'task.updated',
            created_at: '2026-08-05T12:01:00.000Z',
            data: { id: 'T-123', status: 'DONE' },
        }),
        secrets: [SECRET_A, SECRET_B],
    },
    {
        name: 'task_archived_unicode_body',
        description:
            'Non-ASCII body — proves the signed content is UTF-8 encoded identically in both languages.',
        id: 'evt_01J8Z0Q5X8N1V2W3T4Y5Z6A7D0',
        timestamp_seconds: 1785000120,
        raw_body: JSON.stringify({
            id: 'evt_01J8Z0Q5X8N1V2W3T4Y5Z6A7D0',
            type: 'task.archived',
            created_at: '2026-08-05T12:02:00.000Z',
            data: { id: 'T-124', title: 'Café — naïve résumé 😀 日本語' },
        }),
        secrets: [SECRET_A],
    },
    {
        name: 'secret_without_whsec_prefix',
        description:
            'A secret with no whsec_ prefix is base64url-decoded as-is (producer branch coverage).',
        id: 'evt_01J8Z0Q5X8N1V2W3T4Y5Z6A7E1',
        timestamp_seconds: 1785000180,
        raw_body: '{"id":"evt_01J8Z0Q5X8N1V2W3T4Y5Z6A7E1","type":"task.created","data":{}}',
        secrets: [SECRET_NO_PREFIX],
    },
]

const vectors = cases.map((testCase) => ({
    name: testCase.name,
    description: testCase.description,
    id: testCase.id,
    timestamp_seconds: testCase.timestamp_seconds,
    raw_body: testCase.raw_body,
    secrets: testCase.secrets,
    headers: signWebhookPayload({
        id: testCase.id,
        timestampSeconds: testCase.timestamp_seconds,
        rawBody: testCase.raw_body,
        secrets: testCase.secrets,
    }),
}))

const producerSource = join(sourceDir, 'signing.ts')
const producerRevision = (() => {
    try {
        return execFileSync('git', ['-C', monorepo, 'rev-parse', 'HEAD'], {
            encoding: 'utf8',
        }).trim()
    } catch {
        return 'unknown'
    }
})()

process.stdout.write(
    JSON.stringify(
        {
            _comment:
                'CROSS-LANGUAGE VECTORS — generated by IMPORTING the TypeScript producer, packages/api-contracts/src/webhooks/signing.ts, in the GetItDone monorepo (node:crypto HMAC). They prove getitdone_py.webhooks is byte-compatible with the service that signs real deliveries. Regenerate with scripts/generate-webhook-vectors.mjs.',
            producer: 'packages/api-contracts/src/webhooks/signing.ts',
            producer_revision: producerRevision,
            producer_source_bytes: readFileSync(producerSource).length,
            tolerance_seconds: 300,
            vectors,
        },
        null,
        2,
    ) + '\n',
)
