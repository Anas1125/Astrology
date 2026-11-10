const SOURCE_TAG = 'astroai-agpl-preview-2026-11-10';

const SOURCE_URL = `https://github.com/Anas1125/Astrology/tree/${SOURCE_TAG}`;
const LICENSE_URL = `https://github.com/Anas1125/Astrology/blob/${SOURCE_TAG}/LICENSE`;
const THIRD_PARTY_URL = `https://github.com/Anas1125/Astrology/blob/${SOURCE_TAG}/THIRD_PARTY_NOTICES.md`;

export default function SourceLicenseNotice() {
  return (
    <footer className="source-license-notice" aria-label="Source code and license">
      <small>
        Copyright © 2026 AstroAI project contributors. This program is provided without warranty.
        You may redistribute and modify it under the GNU Affero General Public License, version 3 or later.
        {' '}<a href={SOURCE_URL} target="_blank" rel="noopener noreferrer">Source code</a>
        {' · '}<a href={LICENSE_URL} target="_blank" rel="noopener noreferrer">License</a>
        {' · '}<a href={THIRD_PARTY_URL} target="_blank" rel="noopener noreferrer">Third-party notices</a>
      </small>
    </footer>
  );
}
