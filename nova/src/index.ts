// video_gen.js
import { BedrockRuntimeClient, StartAsyncInvokeCommand, GetAsyncInvokeCommand } from "@aws-sdk/client-bedrock-runtime";
import { randomInt } from "crypto";
import fs from "fs";
import sharp from "sharp";


// const REGION = "ap-southeast-2"; // change to region where Nova Reel is enabled
const REGION = "us-east-1";
const MODEL_ID = "amazon.nova-reel-v1:1"; // model ID for Nova Reel :contentReference[oaicite:3]{index=3}

const imgPath = "./resized-haruto-3.png"; // path to your PNG
// const imageBuffer = fs.readFileSync(imgPath);
// const imgBase64 = imageBuffer.toString("base64");
const noTrans = await sharp(imgPath).flatten({ background: { r: 255, g: 255, b: 255 } }).png().toBuffer()
const imgInput = noTrans.toString("base64")

// console.log(imgBase64)
/**
 * Starts a video generation job.
 * @param {BedrockRuntimeClient} client 
 * @param {string} prompt 
 * @param {string} s3OutputUri e.g. "s3://your-bucket/folder-prefix/"
 * @returns {Promise<string>} invocationArn
 */
async function startVideoJob(client: BedrockRuntimeClient, prompt: string, s3OutputUri: string) {
  const seed = randomInt(0, 2147483647); // 0 to 2,147,483,646 :contentReference[oaicite:4]{index=4}

  const modelInput = {
    taskType: "TEXT_VIDEO",
    textToVideoParams: {
      text: prompt,
      images: [
        {
          format: "png",
          source: {
            bytes: imgInput
          }
        }
      ]
    },
    videoGenerationConfig: {
      durationSeconds: 6,  // Currently supported value is 6 seconds :contentReference[oaicite:5]{index=5}
      fps: 24,
      dimension: "1280x720",
      seed: seed,
    }
  };

  const outputDataConfig = {
    s3OutputDataConfig: {
      s3Uri: s3OutputUri
    }
  };

  const command = new StartAsyncInvokeCommand({
    modelId: MODEL_ID,
    modelInput,
    outputDataConfig
  });

  const response = await client.send(command);
  const invocationArn = response.invocationArn;
  console.log(`Started video job. invocationArn = ${invocationArn}`);
  return invocationArn;
}

/**
 * Polls the job status until completion or failure.
 * @param {BedrockRuntimeClient} client 
 * @param {string} invocationArn 
 * @param {number} intervalSeconds Poll interval in seconds
 * @returns {Promise<object>} job status response
 */
async function pollJob(client: BedrockRuntimeClient, invocationArn: any, intervalSeconds = 15) {
  while (true) {
    const cmd = new GetAsyncInvokeCommand({ invocationArn });
    const resp = await client.send(cmd);
    const status = resp.status;
    console.log(`Job status: ${status}`);

    if (status === "Completed") {
      console.log(`Completed! Output S3 URI: ${resp.outputDataConfig?.s3OutputDataConfig?.s3Uri}`);
      return resp;
    } else if (status === "Failed") {
      throw new Error(`Video generation failed: ${resp.failureMessage}`);
    } else {
      // still in progress
      await new Promise(resolve => setTimeout(resolve, intervalSeconds * 1000));
    }
  }
}

async function main() {
  // create Bedrock runtime client
  const client = new BedrockRuntimeClient({ region: REGION });

  const prompt = "Please walk around the column shown in the center of the picture. In detail, go to the left direction, always staring at the column.";
  const s3OutputUri = "s3://branz/output/";

  try {
    const invocationArn = await startVideoJob(client, prompt, s3OutputUri);
    const result = await pollJob(client, invocationArn);
    console.log("Video generation successful:", result);
  } catch (err) {
    // console.error("Bedrock Error:", JSON.stringify(err, null, 2));
    console.error("Error during video generation:", err);
  }
}

// if (require.main === module) {
//   main();
// }
main()