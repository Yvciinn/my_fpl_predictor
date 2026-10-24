const express = require('express')
const router = express.Router()

const PYTHON_API = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000'

router.post('/', async (req, res) => {
    const { message, squad } = req.body || {}

    if (typeof message !== 'string' || !message.trim()) {
        return res.status(400).json({ detail: 'Message is empty.' })
    }
    if (message.length > 500) {
        return res.status(400).json({ detail: 'Message too long (max 500 characters).' })
    }
    if (squad != null && !(Array.isArray(squad) && squad.every(Number.isInteger))) {
        return res.status(400).json({ detail: 'Invalid squad.' })
    }

    try {
        const response = await fetch(`${PYTHON_API}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, squad: squad ?? null })
        })

        const data = await response.json().catch(() => ({}))
        return res.status(response.status).json(data)
    } catch (err) {
        console.error('chat proxy error:', err.message)
        return res.status(502).json({ detail: 'Assistant is offline. Try again later.' })
    }
})

module.exports = router