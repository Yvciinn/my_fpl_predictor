const fs = require('fs')
const path = require('path')
require('dotenv').config({ path: path.join(__dirname, '..', '.env') })

const filePath = path.join(__dirname, '..', '..', 'python', 'outputs', 'best_team.json')
const data = fs.readFileSync(filePath, 'utf8')

const bestTeam = JSON.parse(data)

const connectDb = require("../config/config")
const Prediction = require("../models/Prediction")
const importPrediction = async () =>{

    await connectDb()

    const existing = await Prediction.findOne({
        gameweek: bestTeam.gameweek
    })
    if(existing){
        console.log(`GW ${bestTeam.gameweek} already exist`)
    }
    else {
        await Prediction.create(bestTeam)
        console.log(`GW${bestTeam.gameweek} imported successfully!`)
    }
    process.exit()

}
importPrediction()