#!/bin/bash

#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  export $(cat .env | xargs)
fi

# Run the commands from initialize_aider
export OPENAI_API_KEY="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"
docker pull paulgauthier/aider
docker run -it --user $(id -u):$(id -g) --volume $(pwd):/app paulgauthier/aider --openai-api-key ""
