const express = require('express');
const multer = require('multer');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const cors = require('cors');

const UPLOAD_DIR = path.join(__dirname, 'uploads');
if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR);

const app = express();
app.use(cors());
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// Ovo je važno: frontend path
const frontendPath = path.resolve(__dirname, '../../frontend');
if (!fs.existsSync(frontendPath)) {
    console.warn('⚠️ Frontend folder not found at:', frontendPath);
} else {
    console.log('✅ Frontend folder found at:', frontendPath);
}
app.use(express.static(frontendPath));

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, UPLOAD_DIR),
  filename: (req, file, cb) => cb(null, Date.now() + '-' + file.originalname)
});
const upload = multer({ storage });

app.post('/api/upload', upload.single('image'), (req, res) => {
  if (!req.file) return res.status(400).send({ status: 'no file' });

  const filePath = req.file.path;
  const useAi = req.body.use_ai === '1';
  console.log(`📂 File uploaded: ${filePath}, useAI=${useAi}`);

  const pyPath = path.join(__dirname, '..', 'python', 'ocr_cli.py');
  if (!fs.existsSync(pyPath)) console.error('❌ Python OCR script not found at:', pyPath);

  const py = spawn('python', [pyPath, filePath, useAi ? '--ai' : '--no-ai']);

  let out = '';
  let err = '';
  py.stdout.on('data', data => out += data.toString());
  py.stderr.on('data', data => err += data.toString());

  py.on('close', code => {
    try { fs.unlinkSync(filePath); } catch(e){}
    if (code !== 0) {
        console.error('❌ Python process exited with code', code, 'error:', err);
        return res.status(500).json({ status:'error', result: err || 'ocr failed' });
    }
    console.log('✅ OCR completed successfully');
    return res.json({ status:'ok', result: out });
  });
});

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`🚀 Server running on http://localhost:${port}`));

process.on('uncaughtException', (err) => console.error('Uncaught exception:', err));
process.on('unhandledRejection', (err) => console.error('Unhandled rejection:', err));