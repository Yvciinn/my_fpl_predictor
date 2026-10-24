const express = require("express")

const {getPlayers,getTop,getAll}=require("../controller/players")

const router=express.Router()

router.get("/:gw",getPlayers)
router.get("/:gw/top", getTop)
router.get("/:gw/all",getAll)

module.exports=router