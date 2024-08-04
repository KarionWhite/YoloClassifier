class Logger {
  constructor() {
    this.log = this.log.bind(this);
  }

  log(message) {
    console.log(message);
  }
}