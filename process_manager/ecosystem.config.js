module.exports = {
  apps: [{
    name: "fastapi-app",
    script: "run.py",
    interpreter: "python",
    args: "--service fastapi",
    watch: false,
    instances: 1,
    exec_mode: "fork",
    env: {
      NODE_ENV: "development",
      PYTHONUNBUFFERED: "1"
    },
    env_production: {
      NODE_ENV: "production",
      PYTHONUNBUFFERED: "1"
    }
  }]
}