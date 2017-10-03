protoc collaboration.proto --python_out=collaboration_pb2
protoc registration.proto --python_out=registration_pb2

cd collaboration_pb2
python setup.py install
cd ..

cd registration_pb2
python setup.py install
