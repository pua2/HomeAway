from flask import Flask, jsonify, request
from flask_restful import Api, Resource
import HomeAway
import json

app = Flask(__name__)
api = Api(app)

class LocationPrices(Resource):
    def post(self):
        postedData = request.get_json(force=True)

        address = postedData["address"]
        radius = postedData["radius"]
        propertyJSON = HomeAway.get_json_output(address, radius)
        return jsonify(propertyJSON)

api.add_resource(LocationPrices, '/LocationPrices')

if __name__=="__main__":
    app.run(debug=True)
