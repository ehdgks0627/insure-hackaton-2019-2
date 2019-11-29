from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Float, Boolean
from base64 import b64encode, b64decode
from lane import detect_lane
from PIL import Image
from io import BytesIO
from yolololo import process
from extraction import detect_plate
import io
import base64
import numpy
import random

app = Flask(__name__, static_url_path='/static/', static_folder='templates/static')

app.config['SECRET_KEY'] = 'this is secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()


class Car(db.Model):
    __table_name__ = 'car'

    id = Column(Integer, primary_key=True)

    car_number = Column(String(100), unique=True, nullable=False)
    car_type = Column(String(100), nullable=False)

    # TODO 차량정보 등록

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'id': self.id,
            'car_number': self.car_number
        }

    def __repr__(self):
        return "<Car('{}', '{}')>".format(self.id, self.car_number)


class Record(db.Model):
    __table_name__ = 'record'

    id = Column(Integer, primary_key=True)
    car_id = Column(Integer)
    mainImg = Column(BLOB)
    laneImg = Column(BLOB)
    deepImg = Column(BLOB)
    latitude = Column(Float)
    longitude = Column(Float)
    speed = Column(Float)
    interval = Column(Float)
    degree = Column(Float)
    touch = Column(Boolean)
    inserted_at = Column(DateTime, default=datetime.utcnow())

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'id': self.id,
            'car_id': self.car_id,
            'mainImg': self.mainImg.decode(),
            'laneImg': self.laneImg.decode(),
            'deepImg': self.deepImg.decode(),
            'latitude': self.latitude,
            'longitude': self.longitude,
            'speed': self.speed,
            'interval': self.interval,
            'degree': self.degree,
            'touch': self.touch,
            'inserted_at': self.inserted_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def __repr__(self):
        return "<Record('{}', '{}')>".format(self.id, self.inserted_at)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/callback/oauth', methods=['GET'])
def oauth():
    return render_template('index.html')


@app.route('/getRecord', methods=['POST'])
def get_record():
    record_id = request.json.get('id')
    try:
        record = db.session.query(Record).filter(Record.id == record_id).one()
    except:
        return {}, 500
    return record.serialize


@app.route('/createRecord', methods=['POST'])
def create_record():
    print("STEP1. IN")
    screen = request.json.get('screen')
    image_raw = Image.open(io.BytesIO(b64decode(screen)))

    image = Image.new("RGB", image_raw.size, (255, 255, 255))
    image.paste(image_raw, mask=image_raw.split()[3]) # 3 is the alpha channel

    ori_image = numpy.asarray(image.resize((640, 360)))
    deep_image = numpy.asarray(image.resize((640, 360)))
    image = numpy.asarray(image)

    print("SHAPE > ", image.shape)
    print("STEP2. LANE")

    try:
        touch, degree, final = detect_lane(image)
    except Exception as e:
        touch = False
        final = image
        degree = 30.5
        print(e)

    latitude = request.json.get('latitude')
    longitude = request.json.get('longitude')
    speed = request.json.get('speed')
    interval = request.json.get('interval', 30)

    deepImg = process(deep_image)
    print("STEP3. DEEP")

    record = Record(
        car_id=request.json.get('car_id'),
        mainImg=image_to_base64(Image.fromarray(ori_image, 'RGB')).encode(),
        laneImg=image_to_base64(Image.fromarray(final, 'RGB')).encode(),
        deepImg=image_to_base64(Image.fromarray(deepImg, 'RGB')).encode(),
        touch=touch,
        degree=degree,
        speed=speed,
        interval=interval,
        latitude=latitude,
        longitude=longitude
    )
    db.session.add(record)
    db.session.commit()

    return {'status': True, 'id': record.id}


@app.route('/registerCar', methods=['POST'])
def register_car():
    car = Car(
        car_number=request.json.get('car_number')
    )
    db.session.add(car)
    db.session.commit()

    screen = request.json.get('screen')
    image = Image.open(io.BytesIO(b64decode(screen)))
    image = numpy.asaray(image)
    shape = detect_plate(image)

    from pprint import pprint
    pprint(shape)

    if abs(shape[0][0] - shape[1][0]) < 100:
        return {'status': False}

    return {'status': True, 'shape': shape}


@app.route('/getCar', methods=['POST'])
def get_car():
    data = list(map(lambda x: x.serialize, db.session.query(Car).all()))

    return {'status': True, 'car': data}


if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=8080)
