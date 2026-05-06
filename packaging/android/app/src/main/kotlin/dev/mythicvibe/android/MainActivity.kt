// MainActivity for the mythic-vibe Android wrapper (PH-22.2 foundation).
//
// Single-activity Compose UI. The user types a CLI command into
// a text field, taps Run, the activity invokes the embedded
// Python via Chaquopy on a background coroutine, and streams
// output back into a Text composable.
//
// Foundation-level: command runs synchronously inside the
// coroutine, output is captured to a string, the UI replaces
// the output panel atomically. A future session adds streaming
// stdout (line-by-line append) + concurrent run cancellation
// + a session log.

package dev.mythicvibe.android

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Chaquopy boots the embedded CPython interpreter the
        // first time something invokes Python. Calling start()
        // explicitly in onCreate makes the first-command
        // latency obvious in startup, not in user interaction.
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    MythicVibeApp()
                }
            }
        }
    }
}

@Composable
fun MythicVibeApp() {
    var command by remember { mutableStateOf("--version") }
    var output by remember { mutableStateOf("Press Run to execute a command.") }
    var running by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = "Mythic Vibe CLI",
            style = MaterialTheme.typography.headlineSmall,
        )
        OutlinedTextField(
            value = command,
            onValueChange = { command = it },
            label = { Text("Command (e.g. --version, doctor --json)") },
            singleLine = true,
            modifier = Modifier.fillMaxSize(0.99f),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = {
                    if (running) return@Button
                    running = true
                    output = "Running..."
                    scope.launch {
                        val result = runCli(command)
                        output = result
                        running = false
                    }
                },
                enabled = !running,
            ) {
                Text(if (running) "Running..." else "Run")
            }
        }
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState),
            color = MaterialTheme.colorScheme.surfaceVariant,
        ) {
            Text(
                text = output,
                modifier = Modifier.padding(12.dp),
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

/**
 * Run a mythic-vibe CLI command via Chaquopy and return its
 * captured stdout + stderr as a single string. Errors propagate
 * back into the output text rather than crashing the activity.
 *
 * Foundation-level: synchronous, full-output-then-show. A future
 * session adds line-streaming + cancellation + a session log.
 */
suspend fun runCli(command: String): String = withContext(Dispatchers.IO) {
    try {
        val py = Python.getInstance()
        // The Android-side runner is a small Python helper that
        // captures stdout + stderr from running mythic_vibe_cli.cli.main
        // with the operator's argv. The helper module ships in
        // app/src/main/python/ alongside the manifest.
        val runner = py.getModule("mythic_vibe_cli_android_runner")
        val argv = command.trim().takeIf { it.isNotEmpty() }?.split(" ") ?: emptyList()
        val result = runner.callAttr("run_cli", argv.toTypedArray())
        result.toString()
    } catch (t: Throwable) {
        Log.e("MythicVibe", "CLI invocation failed", t)
        "Error: ${t.message}\n\n${t.stackTraceToString()}"
    }
}
