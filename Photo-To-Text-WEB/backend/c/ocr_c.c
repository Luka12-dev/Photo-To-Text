#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: ocr_c <image>\n");
        return 2;
    }
    char cmd[1024];
    // build command - this relies on the tesseract CLI being available in PATH
    snprintf(cmd, sizeof(cmd), "tesseract \"%s\" stdout -l eng", argv[1]);
    FILE *p = popen(cmd, "r");
    if (!p) {
        fprintf(stderr, "failed to run tesseract\n");
        return 3;
    }
    // stream tesseract stdout to program stdout
    char buf[4096];
    while (fgets(buf, sizeof(buf), p)) {
        fputs(buf, stdout);
    }
    int rc = pclose(p);
    return rc;
}