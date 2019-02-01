#ifndef PIPE_HPP_
#define PIPE_HPP_
#include <iostream>
#include <queue>
#include <utility>
#include <boost/thread.hpp>
#include <boost/thread/mutex.hpp>
#include <boost/thread/locks.hpp>
#include <boost/thread/condition_variable.hpp>

//Since there is a good chance that we will be statically linking, put pipe
//implementation in the header, too avoid static linking/template classes issue
template<class T>
class Pipe {
private:
	std::queue<T> queue;
	boost::mutex mutex;
	boost::condition_variable condition;
	bool done;
public:
	typedef std::pair<T, bool> item;

	Pipe();
	item pop();
	void push(T &t);
	void close();
};

template<class T>
Pipe<T>::Pipe() {
	done = false;
}

template<class T>
std::pair<T, bool> Pipe<T>::pop() {
	boost::unique_lock < boost::mutex > lock(mutex);

	while (queue.empty() && !done) {
		condition.wait(lock);
	}

	if (!queue.empty()) {
		item p = std::make_pair(queue.front(), true);
		queue.pop();
		return p;
	} else if (done) {
		item p;
		p.second = false;
		return p;
	} else {
		std::cerr << "Why on earth did we reach this point in the queue? Damn you synchronization!" << std::endl;
		exit(1);
	}
}

template<class T>
void Pipe<T>::push(T &t) {
	{
		boost::lock_guard < boost::mutex > lock(mutex);
		queue.push(t);
	}
	condition.notify_one();
}

template<class T>
void Pipe<T>::close() {
	{
		boost::lock_guard < boost::mutex > lock(mutex);
		done = true;
	}
	condition.notify_all();
}

#endif /* PIPE_HPP_ */
