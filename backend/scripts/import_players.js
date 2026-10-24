const fs = require('fs')
const path = require('path')
require('dotenv').config({ path: path.join(__dirname, '..', '.env') })

const filePath = path.join(__dirname, '..', '..', 'python', 'outputs', 'players.json')
const data = fs.readFileSync(filePath, 'utf8')

const players = JSON.parse(data)

const connectDb = require("../config/config")
const Player = require('../models/player')

const importPlayer = async () => {
    await connectDb()

    const existing = await Player.findOne({ gameweek: players.gameweek })

    if (existing) {
        console.log(`GW ${players.gameweek} already exists`)
    } else {
        const playersWithGW = players.players.map(p => ({
            ...p,
            gameweek: players.gameweek
        }))
        await Player.insertMany(playersWithGW)
        console.log(`GW${players.gameweek} — ${playersWithGW.length} players imported!`)
    }
    process.exit()
}

importPlayer()