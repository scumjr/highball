CC=g++
CFLAGS=-I. -Wall
LDFLAGS=-L../files/ -Wl,-rpath,../files/ -lprotobuf -lsoda 

all: highball

%.pb.cc: %.proto
	protoc -I=proto/ --cpp_out=proto/ $<

%.pb.o: %.pb.cc
	$(CC) -c -o $@ $<

%.o: %.c
	$(CC) -c -o $@ $< $(CFLAGS)

highball: proto/soda_api.pb.o highball.o patch.o
	$(CC) -o $@ $^ $(LDFLAGS)

clean:
	rm -f highball *.o proto/*.c proto/*.cc proto/*.h proto/*.o
