/*
 * Generate a transcript from an audio input.

 * The audio input is read from stdin as a stream of 1 channel at 44.1 kHz.
 *
 * The transcript is written to stdout in the following JSON format:
 * [ [timestamp1, word1], [timestamp2, word2], ...]
 *
 * Most of this code comes from these projects:
 *
 * - https://github.com/biemster/gasr
 * - https://github.com/marek-g/marek_speech_recognition
 */

#include <iostream>
#include <vector>

#include <err.h>
#include <fcntl.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

#include "proto/soda_api.pb.h"

#define CHANNEL_COUNT 1
#define SAMPLE_RATE   44100
#define CHUNK_SIZE    2048 // 2 chunks per frame, a frame is a single s16

#ifdef __cplusplus
extern "C" {
#endif
typedef void (*RecognitionResultHandler)(const char *serialized_proto, int length,
                                         void *callback_handle);
typedef struct {
    const char *soda_config;
    int soda_config_size;
    RecognitionResultHandler callback;
    void *callback_handle;
} SodaConfig;

extern void *CreateExtendedSodaAsync(SodaConfig config);
extern void DeleteExtendedSodaAsync(void *soda_async_handle);
extern void ExtendedAddAudio(void *soda_async_handle, const char *audio_buffer,
                             int audio_buffer_size);
extern void ExtendedSodaStart(void *soda_async_handle);
extern void ExtendedSodaStop(void *soda_async_handle);
extern void ExtendedSodaMarkDone(void *soda_async_handle);
#ifdef __cplusplus
}
#endif

extern void patch(void);

void resultHandler(const char *serialized_proto, int length, void *callback_handle)
{
    static bool first = true;

    speech::soda::chrome::SodaResponse response;
    if (!response.ParseFromArray(serialized_proto, length)) {
        warnx("Unable to parse result from SODA.");
        return;
    }

    switch (response.soda_type()) {
    case speech::soda::chrome::SodaResponse::START:
        fprintf(stderr, "[*] START\n");
        break;
    case speech::soda::chrome::SodaResponse::STOP:
        fprintf(stderr, "[*] STOP\n");
        break;
    case speech::soda::chrome::SodaResponse::SHUTDOWN:
        fprintf(stderr, "[*] SHUTDOWN\n");
        break;
    case speech::soda::chrome::SodaResponse::ENDPOINT: {
        speech::soda::chrome::SodaEndpointEvent result = response.endpoint_event();
        fprintf(stderr, "[*] endpoint: %d\n", result.endpoint_type());
        break;
    }
    case speech::soda::chrome::SodaResponse::AUDIO_LEVEL: {
        // speech::soda::chrome::SodaAudioLevelInfo info = response.audio_level_info();
        // fprintf(stderr, "[*] AUDIO_LEVEL %f\n", info.rms());
        break;
    }
    case speech::soda::chrome::SodaResponse::RECOGNITION: {
        speech::soda::chrome::SodaRecognitionResult result = response.recognition_result();
        for (int i = 0; i < result.hypothesis_size(); i++) {
            fprintf(stderr, "[%d] %s\n", result.result_type(), result.hypothesis(i).c_str());
            break; // XX
        }
        // fprintf(stderr, "[%d]\n", result.endpoint_reason());
        if (result.result_type() == speech::soda::chrome::SodaRecognitionResult::FINAL) {
            uint64_t start = result.timing_metrics().audio_start_time_usec();
            for (int i = 0; i < result.hypothesis_part_size(); i++) {
                speech::soda::chrome::HypothesisPart part = result.hypothesis_part(i);
                uint64_t offset = part.alignment_ms() * 1000;
                fprintf(stderr, "[+] %ld %s\n", (start + offset) / 1000, part.text(0).c_str());
                if (first) {
                    first = false;
                } else {
                    printf(",");
                }
                printf("\n[%ld, \"%s\"]", (start + offset) / 1000, part.text(0).c_str());
            }
            fflush(stdout);
        }
        break;
    }
    default:
        fprintf(stderr, "resultHandler %d!!!\n", response.soda_type());
        break;
    }

    for (int i = 0; i < response.log_lines_size(); i++) {
        fprintf(stderr, "[>] %s\n", response.log_lines(i).c_str());
    }
}

static void *create_soda_handle(void)
{
    SodaConfig config = { 0 };

    speech::soda::chrome::ExtendedSodaConfigMsg config_msg;
    config_msg.set_channel_count(CHANNEL_COUNT);
    config_msg.set_sample_rate(SAMPLE_RATE);
    config_msg.set_language_pack_directory(
        "../files/1.1.1.5/SODALanguagePacks/fr-FR/1.3045.0/SODAModels/");
    config_msg.set_simulate_realtime_testonly(false);
    config_msg.set_enable_lang_id(false);
    config_msg.set_enable_formatting(true);
    config_msg.set_include_timing_metrics(true);
    config_msg.set_enable_speaker_change_detection(true);
    config_msg.set_recognition_mode(speech::soda::chrome::ExtendedSodaConfigMsg::CAPTION);

    config_msg.set_api_key("");

    auto serialized = config_msg.SerializeAsString();
    config.soda_config = serialized.c_str();
    config.soda_config_size = serialized.size();

    config.callback = resultHandler;
    config.callback_handle = NULL;

    return CreateExtendedSodaAsync(config);
}

static void delay_stream(struct timeval *start_time, size_t *samples_written, size_t len)
{
    struct timeval current_time;
    gettimeofday(&current_time, NULL);

    double elapsed_ms;
    elapsed_ms = (current_time.tv_sec - start_time->tv_sec) * 1000.0;    // sec to ms;
    elapsed_ms += (current_time.tv_usec - start_time->tv_usec) / 1000.0; // usec to ms;

    double dest_time_ms = (*samples_written * 1000) / SAMPLE_RATE;
    if (dest_time_ms > elapsed_ms + 2) {
        usleep((dest_time_ms - elapsed_ms) * 1000);
    }

    *samples_written += len / 2;
}

int main(int argc, char *argv[])
{
    patch();

    void *handle = create_soda_handle();
    if (handle == NULL) {
        return 1;
    }

    freopen(nullptr, "rb", stdin);

    printf("[\n");

    size_t samples_written = 0;
    struct timeval start_time;
    gettimeofday(&start_time, NULL);

    while (1) {
        char audio[CHUNK_SIZE] = {};
        size_t len = fread(audio, sizeof(audio[0]), CHUNK_SIZE, stdin);
        if (len <= 0) {
            break;
        }
        ExtendedAddAudio(handle, audio, len);
        delay_stream(&start_time, &samples_written, len);
    }

    printf("\n]\n");

    DeleteExtendedSodaAsync(handle);

    return 0;
}
