package com.kann.faceiddoor;

import java.io.IOException;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public class ApiClient {
    public static String BASE_URL = "http://10.0.2.2:8000";
    private static final OkHttpClient client = new OkHttpClient();

    public static String postJson(String path, String jsonBody, String token) throws IOException {
        Request.Builder builder = new Request.Builder()
                .url(BASE_URL + path)
                .post(RequestBody.create(jsonBody, MediaType.parse("application/json")));
        if (token != null) builder.addHeader("Authorization", "Bearer " + token);
        Response response = client.newCall(builder.build()).execute();
        String body = response.body() != null ? response.body().string() : "";
        if (!response.isSuccessful()) throw new IOException(body);
        return body;
    }

    public static String get(String path, String token) throws IOException {
        Request.Builder builder = new Request.Builder().url(BASE_URL + path).get();
        if (token != null) builder.addHeader("Authorization", "Bearer " + token);
        Response response = client.newCall(builder.build()).execute();
        String body = response.body() != null ? response.body().string() : "";
        if (!response.isSuccessful()) throw new IOException(body);
        return body;
    }

    public static String patchJson(String path, String jsonBody, String token) throws IOException {
        Request.Builder builder = new Request.Builder()
                .url(BASE_URL + path)
                .patch(RequestBody.create(jsonBody, MediaType.parse("application/json")));
        if (token != null) builder.addHeader("Authorization", "Bearer " + token);
        Response response = client.newCall(builder.build()).execute();
        String body = response.body() != null ? response.body().string() : "";
        if (!response.isSuccessful()) throw new IOException(body);
        return body;
    }

    public static void delete(String path, String token) throws IOException {
        Request.Builder builder = new Request.Builder().url(BASE_URL + path).delete();
        if (token != null) builder.addHeader("Authorization", "Bearer " + token);
        Response response = client.newCall(builder.build()).execute();
        if (!response.isSuccessful()) throw new IOException("Delete failed");
    }
}
