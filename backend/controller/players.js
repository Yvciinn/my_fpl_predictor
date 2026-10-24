const Prediction = require("../models/Prediction")
const Players = require("../models/player")

const getPlayers = async (req, res) => {
    try {
        const all = await Prediction.find()
        const prediction = await Prediction.findOne({ gameweek: req.params.gw })
        if (!prediction) {
            return res.status(404).json({ message: "GW not found" })
        }
        return res.json(prediction)
    } catch (err) {
        return res.status(500).json({ message: err.message })
    }
    
}

const getTop = async (req, res) => {
    try {
        const prediction = await Prediction.findOne({ gameweek: req.params.gw })
        if (!prediction) {
            return res.status(404).json({ message: "GW not found" })
        }
        const gk  = prediction.squad.GK.sort((a, b) => b.predicted_points - a.predicted_points).slice(0, 3)
        const def = prediction.squad.DEF.sort((a, b) => b.predicted_points - a.predicted_points).slice(0, 3)
        const mid = prediction.squad.MID.sort((a, b) => b.predicted_points - a.predicted_points).slice(0, 3)
        const fwd = prediction.squad.FWD.sort((a, b) => b.predicted_points - a.predicted_points).slice(0, 3)
        console.log(prediction.squad.GK[0].id)
        console.log(prediction.squad.DEF[0].id)
        return res.json({ GK: gk, DEF: def, MID: mid, FWD: fwd })
    } catch (err) {
        return res.status(500).json({ message: err.message })
    }
   
}

const getAll = async(req,res) =>{
    try{
        const players= await Players.find({gameweek : req.params.gw})
        if(players){
            return res.json(players)
        }
        else{
            return res.status(404).json({message:"gameweek not found"})
        }


    }
    catch(err){
        return res.status(500).json({message:err.message})
    }


}
module.exports = { getPlayers, getTop,getAll }